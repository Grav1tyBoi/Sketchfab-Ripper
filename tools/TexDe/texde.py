import io
import os
import sys

import numpy as np
import requests
from numba import jit, prange
from PIL import Image

DEBUG_EXPORT_ONLY_TEXTURE = ''

_lut_cache = {}

@jit(nopython=True, cache=True)
def mod(i: int, u: int) -> int:
    y = i // u
    return i - y * u


@jit(nopython=True, cache=True)
def min_val(i: int, t: int) -> int:
    if i < t:
        return i
    else:
        return t


@jit(nopython=True, cache=True)
def max_val(i: int, u: int) -> int:
    if i < u:
        return u
    else:
        return i

@jit(nopython=True, cache=True)
def calc_f(y: int, t: int, f_val: int) -> int:
    """Number of cells covered before reaching diagonal `f_val`."""
    x = min_val(y, t)
    n = max_val(y, t)

    if f_val < x:
        return f_val * (f_val + 1) // 2
    if f_val < n:
        return x * (x + 1) // 2 + x * (f_val - x)

    r = f_val - n
    return x * (x + 1) // 2 + x * (n - x) + (x - 1) * r - (r - 1) * r // 2


@jit(nopython=True, cache=True)
def calc_i(y: int, t: int, x_x: int, x_y: int) -> int:
    """Map tile coordinates (x_x, x_y) to a linear diagonal index."""
    r = min_val(y, t)
    n = max_val(y, t)
    v = x_x + x_y
    h = mod(v, 2) == 0

    if v < r:
        if h:
            return calc_f(y, t, v) + v - x_y
        else:
            return calc_f(y, t, v) + x_y

    if v < n:
        s = t - x_y - 1
        if y < t:
            s = r - (y - x_x)
        if h:
            return calc_f(y, t, v) + s
        else:
            return calc_f(y, t, v) + r - s - 1

    s = t - x_y - 1
    e = r + n - v - 1
    if h:
        return calc_f(y, t, v) + s
    else:
        return calc_f(y, t, v) + e - s - 1


@jit(nopython=True, cache=True)
def calc_u(y: int, t: int, x: int) -> tuple:
    """Inverse of calc_i: linear diagonal index -> (tile_x, tile_y)."""
    v = min_val(y, t)
    r = max_val(y, t)

    if x < v * (v + 1) // 2:
        n = int(((-1) + (1e-06 + np.sqrt(8 * x + 1))) // 2)
        h = x - calc_f(y, t, n)
        s = mod(n, 2) == 0
        if s:
            return (h, n - h)
        else:
            return (n - h, h)

    if x < v * (v + 1) // 2 + v * (r - v):
        x = x - v * (v + 1) // 2
        n = v + x // v
        s = mod(x, v)
        h = mod(n, 2) == 0
        g = n - v + s + 1
        e = v - s - 1
        S = n - s
        T = s
        if y > t:
            if h:
                return (g, e)
            else:
                return (S, T)
        else:
            if h:
                return (T, S)
            else:
                return (e, g)

    n = v * (v - 1) // 2 - (x - (v * (v + 1) // 2 + v * (r - v))) - 1
    s = int(((-1) + np.sqrt(8 * n + 1)) // 2)
    n = r + v - s - 2
    h = x - calc_f(y, t, n)
    g = mod(n, 2) == 0
    e = v + r - n - 1
    if g:
        h = e - h - 1
    S = n + h - y + 1
    return (n - S, S)

@jit(nopython=True, cache=True)
def calc_f_ivec2(v_x: int, v_y: int, uS_x: int, uS_y: int) -> int:
    """Map a (px, py) pixel coordinate to its scrambled linear index."""
    y = uS_x // 8
    t = uS_y // 8
    x = calc_i(y, t, v_x // 8, v_y // 8)
    n = mod(x, 4)

    v_x = mod(v_x, 8)
    v_y = mod(v_y, 8)
    r_x = v_x
    r_y = v_y

    if n == 1:
        r_x = 7 - v_x
    if n == 2:
        r_x = v_y
        r_y = v_x
    if n == 3:
        r_x = 7 - v_y
        r_y = v_x

    return x * 64 + r_x + r_y * 8


@jit(nopython=True, cache=True)
def calc_i_from_index(i: int, uS_x: int, uS_y: int) -> tuple:
    """Inverse of calc_f_ivec2: scrambled linear index -> (px, py)."""
    x = uS_x
    t = uS_y
    v = x * t

    if i < 0:
        i += v
    i = mod(i, v)

    y = x // 8
    n = t // 8
    h = i // 64
    r = i - h * 64
    s = r // 8
    S = r - s * 8
    e = mod(h, 4)

    g = calc_u(y, n, h)
    T_x = g[0] * 8
    T_y = g[1] * 8

    if e == 0:
        T_x += S
        T_y += s
    if e == 1:
        T_x += 7 - S
        T_y += s
    if e == 2:
        T_x += s
        T_y += S
    if e == 3:
        T_x += s
        T_y += 7 - S

    return (T_x, T_y)


@jit(nopython=True, cache=True)
def calc_t(y_x: int, y_y: int, i: int, uS_x: int, uS_y: int) -> int:
    """Apply offset `i` (in the scrambled space) and wrap into [0, w*h)."""
    v = uS_x * uS_y
    n = calc_f_ivec2(y_x, y_y, uS_x, uS_y) + i

    if n > v:
        n -= v
    if n < 0:
        n += v

    if n > v:
        return -1
    if n < 0:
        return -2
    return n

@jit(nopython=True, parallel=True, cache=True)
def build_lookup_table(width: int, height: int, offset: int, flip_y: bool) -> np.ndarray:
    """Precompute, for each output pixel, the source (x, y) in the input image."""
    lut = np.zeros((height, width, 2), dtype=np.int32)

    for py in prange(height):
        for px in range(width):
            y_x = px
            y_y = py
            if flip_y:
                y_y = height - py - 1

            if offset == -1:
                lut[py, px, 0] = y_x
                lut[py, px, 1] = y_y
            else:
                n = calc_t(y_x, y_y, offset, width, height)
                if n >= 0:
                    src_coords = calc_i_from_index(n, width, height)
                    lut[py, px, 0] = src_coords[0]
                    lut[py, px, 1] = src_coords[1]
                else:
                    lut[py, px, 0] = -1
                    lut[py, px, 1] = -1

    return lut


@jit(nopython=True, parallel=True, cache=True)
def apply_lookup_table(input_pixels: np.ndarray, output_pixels: np.ndarray,
                       lut: np.ndarray, width: int, height: int):
    """Copy pixels from input to output following the precomputed LUT."""
    for py in prange(height):
        for px in range(width):
            src_x = lut[py, px, 0]
            src_y = lut[py, px, 1]

            if 0 <= src_x < width and 0 <= src_y < height:
                for c in range(4):
                    output_pixels[py, px, c] = input_pixels[src_y, src_x, c]
            else:
                output_pixels[py, px, 0] = 255
                output_pixels[py, px, 1] = 0
                output_pixels[py, px, 2] = 0
                output_pixels[py, px, 3] = 255



def decode_texture(image: Image.Image, pk: int) -> Image.Image:
    """Decode a single scrambled Sketchfab texture using its `pk` as the seed."""
    width, height = image.size

    image_rgba = image.convert('RGBA')
    input_pixels = np.array(image_rgba, dtype=np.uint8)
    output_pixels = np.zeros_like(input_pixels)

    if pk:
        e = pk * 64
        e %= width * height
        offset = -e
    else:
        offset = -1

    cache_key = (width, height, offset)
    if cache_key in _lut_cache:
        lut = _lut_cache[cache_key]
    else:
        lut = build_lookup_table(width, height, offset, True)
        _lut_cache[cache_key] = lut

    apply_lookup_table(input_pixels, output_pixels, lut, width, height)
    output_pixels = np.flip(output_pixels, axis=0)

    return Image.fromarray(output_pixels)


def get_model_textures(model_id: str) -> dict:
    """Fetch the texture metadata JSON for a Sketchfab model."""
    resp = requests.get(f'https://sketchfab.com/i/models/{model_id}/textures')
    resp.raise_for_status()
    array = resp.json()

    if DEBUG_EXPORT_ONLY_TEXTURE:
        array['results'] = [
            t for t in array['results']
            if t['name'] == DEBUG_EXPORT_ONLY_TEXTURE
        ]

    return array


def process_texture(texture_info: dict, output_dir: str) -> bool:
    """Download, decode and save the largest valid variant of one texture."""
    filesize = 0
    image_url = None
    pk = None

    for t in texture_info['images']:
        if (t['width'] / 16).is_integer() and (t['height'] / 16).is_integer() and (t['size'] > filesize):
            filesize = t['size']
            image_url = t['url']
            pk = t['pk']

    if image_url is None:
        return False

    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        content = response.raw.read()

        image = Image.open(io.BytesIO(content))
        decoded = decode_texture(image, pk)

        output_path = os.path.join(
            output_dir,
            f"{texture_info['uid']}_{texture_info['name']}",
        )
        os.makedirs(output_dir, exist_ok=True)

        try:
            decoded.save(output_path)
        except OSError:
            decoded.convert('RGB').save(output_path)
    except Exception as e:
        print(f"  Error processing {texture_info['uid']}_{texture_info['name']}: {e}")
        return False

    return True

def export_textures(url, output_dir):
    model_id = url[url.rfind('-') + 1:]
    textures = get_model_textures(model_id)
    if not textures['results']:
        sys.exit(1)

    success_count = 0
    total = len(textures['results'])
    for i, texture in enumerate(textures['results'], 1):
        if process_texture(texture, output_dir):
            print(f"Processed {i}/{total}: {texture['uid']}_{texture['name']}")
            success_count += 1