global thumbnail_download
global blender_path
global fbx_export
global quads_recreation
global custom_download_folder

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QProgressBar, QFileDialog, QMessageBox, QCheckBox,
    QStackedWidget, QListWidget, QListWidgetItem, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import QTimer, Qt, QThread, Signal, Slot, QSize
from PySide6.QtGui import QPixmap, QImage, QIcon, QColor, QFont, QPainter, QPainterPath
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import configparser
import os
import shutil
import subprocess
import json
import sys
import time
from tools.TexDe.texde import export_textures

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


blender_script = resource_path('blender_shading.py')
binz_decrypt = resource_path('tools\\binz\\binzDecrypt.exe')
binz_osg = resource_path('tools\\binz\\binzOsg.exe')
osgconv = resource_path('tools\\OsgConv\\osgconv.exe')
CONFIG_FILE = 'config.ini'

config = configparser.ConfigParser()
if os.path.exists(CONFIG_FILE):
    config.read(CONFIG_FILE)
if not config.has_section('Paths'):
    config.add_section('Paths')
    config.set('Paths', 'blender', '')
    config.set('Paths', 'custom_download_folder', '')
    config.set('Paths', 'fbx_export', 'true')
    config.set('Paths', 'thumbnail_download', 'true')
    config.set('Paths', 'quads_recreation', 'false')
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

blender_path = config.get('Paths', 'blender', fallback='')
custom_download_folder = config.get('Paths', 'custom_download_folder', fallback='')
fbx_export = config.get('Paths', 'fbx_export', fallback='true').lower() == 'true'
thumbnail_download = config.get('Paths', 'thumbnail_download', fallback='true').lower() == 'true'
quads_recreation = config.get('Paths', 'quads_recreation', fallback='false').lower() == 'true'

STYLESHEET = """
* {
    font-family: -apple-system, "SF Pro Text", "Segoe UI", "Helvetica Neue", sans-serif;
    color: #1d1d1f;
    font-size: 13px;
}

QWidget#Root {
    background-color: #f5f5f7;
}

/* Sidebar */
QFrame#Sidebar {
    background-color: #ececee;
    border-right: 1px solid #e0e0e3;
}
QLabel#AppTitle {
    font-size: 15px;
    font-weight: 600;
    color: #1d1d1f;
    padding: 4px 4px 12px 4px;
}
QPushButton#NavButton {
    background: transparent;
    border: none;
    text-align: left;
    padding: 8px 12px;
    border-radius: 6px;
    color: #1d1d1f;
    font-size: 13px;
}
QPushButton#NavButton:hover {
    background-color: #dcdce0;
}
QPushButton#NavButton:checked {
    background-color: #007aff;
    color: white;
    font-weight: 500;
}

/* Cards */
QFrame#Card {
    background-color: #ffffff;
    border: 1px solid #e5e5e7;
    border-radius: 10px;
}

/* Page header */
QLabel#PageTitle {
    font-size: 22px;
    font-weight: 600;
    color: #1d1d1f;
}
QLabel#PageSubtitle {
    font-size: 13px;
    color: #6e6e73;
}
QLabel#SectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #6e6e73;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel#FieldLabel {
    font-size: 13px;
    color: #1d1d1f;
}
QLabel#Hint {
    font-size: 11px;
    color: #8e8e93;
}

/* Inputs */
QLineEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #007aff;
    selection-color: white;
    min-height: 20px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #007aff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: white;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    selection-background-color: #007aff;
    selection-color: white;
    outline: 0;
    padding: 4px;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 6px 14px;
    color: #1d1d1f;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #f5f5f7;
    border-color: #b8b8bd;
}
QPushButton:pressed {
    background-color: #e8e8eb;
}
QPushButton:disabled {
    color: #b0b0b5;
    background-color: #f5f5f7;
}
QPushButton#Primary {
    background-color: #007aff;
    color: white;
    border: 1px solid #007aff;
    font-weight: 500;
}
QPushButton#Primary:hover {
    background-color: #1a8aff;
    border-color: #1a8aff;
}
QPushButton#Primary:pressed {
    background-color: #0066d6;
    border-color: #0066d6;
}
QPushButton#Primary:disabled {
    background-color: #b8d6ff;
    border-color: #b8d6ff;
    color: #ffffff;
}
QPushButton#Danger {
    color: #ff3b30;
}
QPushButton#Danger:hover {
    background-color: #fff0ee;
    border-color: #ff3b30;
}
QPushButton#Subtle {
    background: transparent;
    border: none;
    color: #007aff;
    padding: 4px 8px;
}
QPushButton#Subtle:hover {
    color: #1a8aff;
    text-decoration: underline;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #1d1d1f;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    background: white;
}
QCheckBox::indicator:hover {
    border-color: #007aff;
}
QCheckBox::indicator:checked {
    background-color: #007aff;
    border-color: #007aff;
    image: none;
}

/* Progress bar */
QProgressBar {
    background-color: #e5e5e7;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #007aff;
    border-radius: 3px;
}

/* Status pills (set via objectName) */
QLabel#StatusPill {
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}
QLabel#StatusPillQueued {
    background-color: #e5e5e7;
    color: #6e6e73;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}
QLabel#StatusPillRunning {
    background-color: #cfe5ff;
    color: #0066d6;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}
QLabel#StatusPillDone {
    background-color: #d4f3dd;
    color: #1d8338;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}
QLabel#StatusPillFailed {
    background-color: #ffe1de;
    color: #c8281f;
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}

/* List */
QListWidget {
    background: transparent;
    border: none;
    outline: 0;
}
QListWidget::item {
    padding: 0;
    margin: 0 0 8px 0;
    border-radius: 8px;
}

/* Scroll area */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c7c7cc;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #aeaeb2;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""

class DownloadThread(QThread):
    progress_signal = Signal(int)
    text_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, url_entry_text):
        super().__init__()
        self.url_entry_text = url_entry_text
        self.cancel_flag = False
        self.processes = []

    @Slot()
    def cancel(self):
        self.cancel_flag = True
        for proc in self.processes:
            try:
                proc.kill()
            except Exception:
                pass

    def run(self):
        def run_subprocess(cmd, cwd=None):
            creation_flags = 0
            if sys.platform.startswith('win'):
                creation_flags = subprocess.CREATE_NO_WINDOW
            proc = subprocess.Popen(cmd, cwd=cwd, creationflags=creation_flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.processes.append(proc)
            while True:
                if self.cancel_flag:
                    proc.kill()
                    raise Exception('Cancelled')
                else:
                    line = proc.stdout.readline()
                    if line:
                        print(line.rstrip())
                    ret = proc.poll()
                    if ret is not None:
                        for line in proc.stdout:
                            print(line.rstrip())
                        break
                    QThread.msleep(10)
            if proc in self.processes:
                self.processes.remove(proc)

        url = self.url_entry_text

        def run_download():
            def set_progress(value):
                self.progress_signal.emit(value)

            def set_text(txt):
                self.text_signal.emit(txt)

            def startclean(dlpath):
                for root_dir, dirs, files in os.walk(dlpath):
                    for f in files:
                        os.remove(os.path.join(root_dir, f))
                    for d in dirs:
                        shutil.rmtree(os.path.join(root_dir, d))

            def cleanup(dlpath):
                filelist = [f for f in os.listdir(dlpath) if not any((f.endswith(ext) for ext in ['.gltf', '.fbx', '.blend', 'textures', '.json', '.stl', '.jpg']))]
                for f in filelist:
                    cpath = os.path.join(dlpath, f)
                    if os.path.isfile(cpath):
                        os.remove(cpath)
                    else:
                        shutil.rmtree(cpath)

            def binzDecryption(dlpath, filename):
                keypath = os.path.join(dlpath, 'key.txt')
                filepath = os.path.join(dlpath, filename)
                run_subprocess([binz_decrypt, keypath, filepath], cwd=dlpath)

            def textures_RIP(url, dlpath):
                output = os.path.join(dlpath, 'textures')
                os.makedirs(output, exist_ok=True)
                print(output)
                export_textures(url, output)

            def osgjs2gltf(dlpath, model_name='file'):
                osgjs = os.path.join(dlpath, 'file.osgjs')
                output = os.path.join(dlpath, f'{model_name}.gltf')
                run_subprocess([osgconv, osgjs, output, '-O', 'XParam=939161269', '-O', 'NoTextureLoad'], cwd=dlpath)
                try:
                    gltf_path = output
                    mat_info_path = os.path.join(dlpath, 'mat_info.json')
                    print(mat_info_path)
                    print(f'GLTF: {os.path.exists(gltf_path)}')
                    print(f'Mat Info: {os.path.exists(mat_info_path)}')
                    if os.path.exists(gltf_path) and os.path.exists(mat_info_path):
                        print('Both files exist, proceeding with URI update')
                        with open(gltf_path, 'r', encoding='utf-8') as gf:
                            gltf = json.load(gf)
                        with open(mat_info_path, 'r', encoding='utf-8') as mf:
                            mat_info = json.load(mf)
                        images = gltf.get('images', [])
                        print(f'Found {len(images)} images in glTF')
                        for img in images:
                            uri = img.get('uri', '')
                            if not uri or '/' not in uri:
                                continue
                            else:
                                short = uri.split('/')[-1].split('.')[0]
                                found = None
                                for mname, channels in mat_info.items():
                                    if not isinstance(channels, dict):
                                        continue
                                    else:
                                        for chname, chval in channels.items():
                                            if isinstance(chval, dict) and 'texture' in chval:
                                                texname = chval.get('texture', '')
                                                if short in texname:
                                                    found = texname
                                                    break
                                        if found:
                                            break
                                if found:
                                    img['uri'] = 'textures/' + found
                        with open(gltf_path, 'w', encoding='utf-8') as gf:
                            json.dump(gltf, gf, indent=2)
                except Exception:
                    pass
                if config.get('Paths', 'fbx_export', fallback='true').lower() == 'true':
                    output2 = os.path.join(dlpath, f'{model_name}.fbx')
                    run_subprocess([osgconv, osgjs, output2], cwd=dlpath)

            def rename_file(filepath, newname):
                directory = os.path.dirname(filepath)
                new_filepath = os.path.join(directory, newname)
                os.rename(filepath, new_filepath)

            def matclean(dlpath):
                blacklist = {'SpecularColor', 'Matcap', 'DiffuseIntensity', 'DiffuseColor', 'SpecularHardness'}

                def load_json(file_path):
                    with open(file_path) as file:
                        return json.load(file)

                def get_texture_info(texture_uid):
                    for texture in texture_info['results']:
                        if texture['uid'] == texture_uid:
                            return texture

                def matwrite(value):
                    entry = {'factor': value.get('factor')}
                    if 'texture' in value:
                        texture = get_texture_info(value['texture'].get('uid'))
                        if texture:
                            entry['texture'] = f"{texture['uid']}_{texture['name']}"
                            entry['texture_type'] = value['texture'].get('internalFormat')
                    for key in ['occludeSpecular', 'color', 'flipY', 'type', 'ior']:
                        if key in value:
                            entry[key] = value[key] if key != 'color' else value[key] + [1]
                    return entry

                def aufraeumen(data):
                    werte = {}
                    SheenOn = ClearCoatOn = False
                    channels = data.get('channels', {})
                    for key, value in channels.items():
                        if key in blacklist or not value.get('enable'):
                            continue
                        else:
                            if key == 'Sheen':
                                SheenOn = True
                            else:
                                if key == 'ClearCoat':
                                    ClearCoatOn = True
                            if key == 'SheenRoughness' and SheenOn or (key == 'ClearCoatNormalMap' and ClearCoatOn) or (key == 'ClearCoatRoughness' and ClearCoatOn) or (key not in {'SheenRoughness', 'ClearCoatNormalMap', 'ClearCoatRoughness'}):
                                werte[key] = matwrite(value)
                    return werte

                model_info = load_json(os.path.join(dlpath, 'viewer_info.json'))
                texture_info = load_json(os.path.join(dlpath, 'texture_info.json'))
                Json_Final = {material['name']: aufraeumen(material) for name, material in model_info['options']['materials'].items() if name != 'updatedAt'}
                with open(os.path.join(dlpath, 'mat_info.json'), 'w') as f:
                    json.dump(Json_Final, f, indent=4)

            def line_change(dlpath, key, var, key2, var2):
                script_path = os.path.join(dlpath, 'blender_shading.py')
                with open(script_path, 'r') as file:
                    lines = file.readlines()
                with open(script_path, 'w') as file:
                    for line in lines:
                        if line.strip().startswith(f'{key} ='):
                            line = f'{key} = R\"{var}\"\n'
                        if line.strip().startswith(f'{key2} ='):
                            line = f'{key2} = R\"{var2}\"\n'
                        file.write(line)

            def get_base_path():
                if getattr(sys, 'frozen', False):
                    return os.path.dirname(sys.executable)
                else:
                    return os.path.dirname(os.path.abspath(__file__))

            def main(url):
                Newmodel = True
                set_progress(0)
                set_text('Download Keys and Json Files')

                pypath = get_base_path()
                if config['Paths']['custom_download_folder'] != '':
                    dlpath = config['Paths']['custom_download_folder']
                else:
                    if not os.path.isdir(os.path.join(pypath, 'downloads')):
                        os.makedirs(os.path.join(pypath, 'downloads'))
                    dlpath = os.path.join(pypath, 'downloads')
                model_name = url.split('/')[-1]

                if not os.path.isdir(os.path.join(dlpath, model_name)):
                    os.makedirs(os.path.join(dlpath, model_name))
                dlpath = os.path.join(dlpath, model_name)

                try:
                    if self.cancel_flag:
                        raise Exception('Cancelled')

                    id = url.split('-')[-1]
                    startclean(dlpath)
                    embed = f'https://sketchfab.com/models/{id}/embed'
                    embed_file = requests.get(embed).text
                    line_to_find = ' <div class=\"dom-data-container\" style=\"display:none;\" id=\"js-dom-data-prefetched-data\"><!--'
                    viewer_info = embed_file.split(line_to_find)[1].split('-->')[0]
                    viewer_info = json.loads(viewer_info.replace('&#34;', '\"'))[f'/i/models/{id}']

                    with open(os.path.join(dlpath, 'viewer_info.json'), 'w') as f:
                        json.dump(viewer_info, f, indent=4)

                    if thumbnail_download:
                        thumbnail_url = viewer_info.get('thumbnails', {}).get('images', [{}])[0].get('url')
                        if thumbnail_url:
                            thumb_response = requests.get(thumbnail_url)
                            with open(os.path.join(dlpath, 'thumbnail.jpg'), 'wb') as f:
                                f.write(thumb_response.content)

                    textureInfo = requests.get(f'https://sketchfab.com/i/models/{id}/textures').json()
                    with open(os.path.join(dlpath, 'texture_info.json'), 'w') as x:
                        json.dump(textureInfo, x, indent=4)

                    modelInfo = requests.get(f'https://sketchfab.com/i/models/{id}').json()
                    with open(os.path.join(dlpath, 'model_info.json'), 'w') as x:
                        json.dump(modelInfo, x, indent=4)

                    try:
                        key1 = viewer_info['files'][0]['p'][0]['b']
                    except KeyError:
                        Newmodel = False

                    if Newmodel:
                        with open(os.path.join(dlpath, 'key.txt'), 'w') as x:
                            x.write(key1)
                        for k in embed_file.splitlines():
                            if '<script src=' in k:
                                js_file = requests.get(k.split('\"  crossorigin=\"anonymous\"></script>')[0].split('<script src=\"')[-1]).text
                                if 'pXZ0:(e,t,a)=>{\"use strict\";a.d(t,{k:()=>n});const n=' in js_file:
                                    key2 = js_file.split('const n=\"')[-1].split('\\n\"}')[0]
                                    with open(os.path.join(dlpath, 'key2.txt'), 'w') as x:
                                        x.write(key2)
                                    break

                    set_progress(12)
                    set_text('Download Binz and Decrypt')
                    if self.cancel_flag:
                        raise Exception('Cancelled')

                    if Newmodel:
                        binz_url = viewer_info['files'][0]['osgjsUrl']
                        file_urls = [binz_url, binz_url.replace('file.binz', 'model_file.binz'), binz_url.replace('file.binz', 'model_file_wireframe.binz')]
                    else:
                        binz_url = viewer_info['files'][0]['osgjsUrl']
                        file_urls = [binz_url, binz_url.replace('file.osgjs.gz', 'model_file.bin.gz'), binz_url.replace('file.osgjs.gz', 'model_file_wireframe.bin.gz')]

                    for file_url in file_urls:
                        filename = file_url.split('/')[-1]
                        response = requests.get(file_url)
                        with open(os.path.join(dlpath, filename), 'wb') as f:
                            f.write(response.content)
                        if Newmodel:
                            binzDecryption(dlpath, filename)
                        else:
                            rename_file(os.path.join(dlpath, filename), filename.split('.gz')[0])

                    set_progress(25)
                    set_text('Download Animations')
                    if self.cancel_flag:
                        raise Exception('Cancelled')

                    with open(os.path.join(dlpath, 'animation.html'), 'w', encoding='utf-8') as a:
                        a.write(embed_file)
                    with open(os.path.join(dlpath, 'animation.html'), 'r', encoding='utf-8') as a:
                        animtext = a.read()

                    animtext = animtext.split(line_to_find)[1].split('-->')[0].replace('&#34;', '\n')
                    animlist = [i for i in animtext.splitlines() if '/animations/' in i]
                    os.makedirs(os.path.join(dlpath, 'animations'), exist_ok=True)
                    animpath = os.path.join(dlpath, 'animations')

                    for i in animlist:
                        ar = requests.get(i)
                        open(os.path.join(animpath, i.split('/')[-1].split('.gz')[0]), 'wb').write(ar.content)

                    set_progress(37)
                    set_text('Download and Decrypt Textures')
                    if self.cancel_flag:
                        raise Exception('Cancelled')

                    os.makedirs(os.path.join(dlpath, 'textures'), exist_ok=True)
                    textures_RIP(url, dlpath)

                    matclean(dlpath)
                    set_progress(75)
                    set_text('Convert OSGJS')
                    if self.cancel_flag:
                        raise Exception('Cancelled')

                    osgjs2gltf(dlpath, model_name)

                    shutil.copyfile(blender_script, os.path.join(dlpath, 'blender_shading.py'))
                    line_change(dlpath, 'folder_path', dlpath, 'model_name', model_name)

                    stl_export_val = config.get('Paths', 'stl_export', fallback='false').lower() == 'true'
                    stl_size_val = config.get('Paths', 'stl_size', fallback='100')
                    line_change(dlpath, 'STL_export', str(stl_export_val), 'STL_size', str(stl_size_val))

                    with open(os.path.join(dlpath, 'model_info.json'), 'r') as f:
                        model_info = json.load(f)

                    metadata = model_info.get('metadata', {})
                    quad = metadata.get('quad', 0)
                    triangle = metadata.get('triangle', 0)
                    polygon = metadata.get('polygon', 0)
                    total = quad + triangle + polygon

                    if total > 0:
                        quad_percentage = quad / total
                        print(f'Quad Percentage: {quad_percentage:.2f}')
                        if quad_percentage > 0.75 and config.get('Paths', 'quads_recreation', fallback='false').lower() == 'true':
                            quad_val = True
                        else:
                            quad_val = False
                    else:
                        quad_val = False

                    line_change(dlpath, 'quad_recreation', str(quad_val), 'fbx_export', str(fbx_export))
                    config.read('config.ini')
                    self.text_signal.emit(f"Blender path: {config['Paths']['blender']}")

                    if config['Paths']['blender'] != '':
                        blender = config['Paths']['blender'] + '\\\\blender.exe'
                        set_progress(90)
                        set_text('Create Blend File')
                        run_subprocess([blender, '-b', '-P', 'blender_shading.py'], cwd=dlpath)

                    cleanup(dlpath)
                    set_progress(100)
                    set_text('Download Done')

                except Exception as e:
                    if str(e) == 'Cancelled':
                        if os.path.exists(dlpath):
                            shutil.rmtree(dlpath)
                        set_text('Download cancelled')
                        set_progress(0)
                        return None
                    else:
                        import traceback
                        with open('error.log', 'a') as f:
                            f.write(traceback.format_exc() + '\n')
                        self.text_signal.emit(f'Error: {e}')
                finally:
                    if os.path.isdir(dlpath):
                        try:
                            cleanup(dlpath)
                        except Exception:
                            pass

            if url.split('.')[-1] == 'json':
                with open(url) as l:
                    links = json.load(l)
                for link in links:
                    main(link)
            else:
                if url.split('.')[-1] == 'txt':
                    with open(os.path.join(url), 'r', encoding='utf-8') as l:
                        for link in l:
                            main(link.strip())
                else:
                    main(url)

        run_download()
        self.finished_signal.emit()


def create_placeholder_image(size, text='No Image'):
    width, height = size
    ratio = 1.7777777777777777
    if width / height > ratio:
        new_height = int(width / ratio)
        new_width = width
    else:
        new_width = int(height * ratio)
        new_height = height
    img = Image.new('RGB', (new_width, new_height), color=(235, 235, 238))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
    position = ((new_width - text_width) // 2, (new_height - text_height) // 2)
    draw.text(position, text, fill=(110, 110, 115), font=font)
    return img


def pil_to_qpixmap(pil_img):
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    qimage = QImage(
        pil_img.tobytes('raw', 'RGB'),
        pil_img.width,
        pil_img.height,
        pil_img.width * 3,
        QImage.Format_RGB888,
    )
    return QPixmap.fromImage(qimage.copy())


def make_card(parent=None):
    """A white rounded panel."""
    card = QFrame(parent)
    card.setObjectName('Card')
    return card

class Sidebar(QFrame):
    nav_changed = Signal(int)  # page index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('Sidebar')
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(2)

        title = QLabel('Sketchfab v2.5')
        title.setObjectName('AppTitle')
        layout.addWidget(title)

        self.buttons = []
        for idx, (label, _) in enumerate([
            ('  Download', 0),
            ('  Queue', 1),
            ('  User Lists', 2),
            ('  Settings', 3),
        ]):
            btn = QPushButton(label)
            btn.setObjectName('NavButton')
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=idx: self._on_click(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch(1)
        self.buttons[0].setChecked(True)

    def _on_click(self, index):
        for i, b in enumerate(self.buttons):
            b.setChecked(i == index)
        self.nav_changed.emit(index)

STATUS_QUEUED, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED, STATUS_CANCELLED = (
    'queued', 'running', 'done', 'failed', 'cancelled'
)

_STATUS_LABEL = {
    STATUS_QUEUED: ('Queued', 'StatusPillQueued'),
    STATUS_RUNNING: ('Running', 'StatusPillRunning'),
    STATUS_DONE: ('Done', 'StatusPillDone'),
    STATUS_FAILED: ('Failed', 'StatusPillFailed'),
    STATUS_CANCELLED: ('Cancelled', 'StatusPillFailed'),
}


class QueueItemCard(QFrame):
    """Inline card representing one queued/running/finished download."""

    cancel_requested = Signal(object)  # emits self
    remove_requested = Signal(object)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.setObjectName('Card')
        self.source = source
        self.status = STATUS_QUEUED
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        # Top row: name + status pill
        top = QHBoxLayout()
        top.setSpacing(10)

        display = self.source
        if display.startswith('http'):
            display = display.rstrip('/').split('/')[-1] or display
        elif os.path.isfile(display):
            display = os.path.basename(display)

        self.name_label = QLabel(display)
        f = QFont()
        f.setPointSize(13)
        f.setWeight(QFont.DemiBold)
        self.name_label.setFont(f)
        self.name_label.setToolTip(self.source)
        top.addWidget(self.name_label, 1)

        self.status_pill = QLabel('Queued')
        self.status_pill.setObjectName('StatusPillQueued')
        self.status_pill.setAlignment(Qt.AlignCenter)
        top.addWidget(self.status_pill)

        outer.addLayout(top)

        # Status text + progress
        self.status_text = QLabel('Waiting in queue…')
        self.status_text.setObjectName('Hint')
        outer.addWidget(self.status_text)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)

        # Bottom action row
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.action_btn = QPushButton('Cancel')
        self.action_btn.setObjectName('Danger')
        self.action_btn.clicked.connect(self._on_action)
        bottom.addWidget(self.action_btn)
        outer.addLayout(bottom)

    def _on_action(self):
        if self.status in (STATUS_QUEUED, STATUS_RUNNING):
            self.cancel_requested.emit(self)
        else:
            self.remove_requested.emit(self)

    def set_status(self, status):
        self.status = status
        label, obj_name = _STATUS_LABEL[status]
        self.status_pill.setText(label)
        self.status_pill.setObjectName(obj_name)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

        if status == STATUS_DONE:
            self.action_btn.setText('Remove')
            self.action_btn.setObjectName('')
            self.status_text.setText('Completed')
            self.progress.setValue(100)
        elif status == STATUS_FAILED:
            self.action_btn.setText('Remove')
            self.action_btn.setObjectName('')
        elif status == STATUS_CANCELLED:
            self.action_btn.setText('Remove')
            self.action_btn.setObjectName('')
            self.status_text.setText('Cancelled')
        elif status == STATUS_RUNNING:
            self.action_btn.setText('Cancel')
            self.action_btn.setObjectName('Danger')
        elif status == STATUS_QUEUED:
            self.action_btn.setText('Cancel')
            self.action_btn.setObjectName('Danger')

        self.action_btn.style().unpolish(self.action_btn)
        self.action_btn.style().polish(self.action_btn)

    def set_progress(self, v):
        self.progress.setValue(v)

    def set_text(self, t):
        self.status_text.setText(t)

class DownloadPage(QWidget):
    queue_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._fetched_pixmap = None

        self.fetch_timer = QTimer(self)
        self.fetch_timer.setSingleShot(True)
        self.fetch_timer.timeout.connect(self.fetch_image)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel('Download')
        title.setObjectName('PageTitle')
        outer.addWidget(title)

        subtitle = QLabel('Paste a model URL, choose a saved user list, or load a links file.')
        subtitle.setObjectName('PageSubtitle')
        outer.addWidget(subtitle)

        # Preview card
        preview_card = make_card()
        pv_layout = QVBoxLayout(preview_card)
        pv_layout.setContentsMargins(0, 0, 0, 0)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setMinimumHeight(260)
        self.thumbnail_label.setStyleSheet(
            "border-top-left-radius: 10px; border-top-right-radius: 10px;"
            "background: #ebebee;"
        )
        self._set_placeholder()
        pv_layout.addWidget(self.thumbnail_label)

        # Input row inside the same card, below the image
        form = QWidget()
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(20, 18, 20, 20)
        form_layout.setSpacing(10)

        self.mode_dropdown = QComboBox()
        self.mode_dropdown.addItems(['URL', 'User List', 'Links File (.json / .txt)'])
        self.mode_dropdown.currentIndexChanged.connect(self._on_mode_changed)

        # Two-column grid via QGridLayout for clean alignment.
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        mode_label = QLabel('Source')
        mode_label.setObjectName('FieldLabel')
        grid.addWidget(mode_label, 0, 0, Qt.AlignVCenter)
        grid.addWidget(self.mode_dropdown, 0, 1)

        # Stacked input area: line edit, user-list dropdown, file picker
        self.input_stack = QStackedWidget()

        # Page 0: URL line edit
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText('https://sketchfab.com/3d-models/...')
        self.url_entry.textChanged.connect(lambda: self.fetch_timer.start(500))
        self.input_stack.addWidget(self.url_entry)

        # Page 1: user list dropdown
        ul_widget = QWidget()
        ul_layout = QHBoxLayout(ul_widget)
        ul_layout.setContentsMargins(0, 0, 0, 0)
        self.userlist_dropdown = QComboBox()
        ul_layout.addWidget(self.userlist_dropdown, 1)
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh_user_lists)
        ul_layout.addWidget(refresh_btn)
        self.input_stack.addWidget(ul_widget)

        # Page 2: file picker
        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText('Path to .json or .txt')
        file_layout.addWidget(self.file_entry, 1)
        browse_btn = QPushButton('Browse…')
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        self.input_stack.addWidget(file_widget)

        input_label = QLabel('Input')
        input_label.setObjectName('FieldLabel')
        grid.addWidget(input_label, 1, 0, Qt.AlignVCenter | Qt.AlignTop)
        grid.addWidget(self.input_stack, 1, 1)

        form_layout.addLayout(grid)

        # Action row
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.download_btn = QPushButton('Add to Queue')
        self.download_btn.setObjectName('Primary')
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self._on_download_clicked)
        action_row.addWidget(self.download_btn)
        form_layout.addLayout(action_row)

        pv_layout.addWidget(form)
        outer.addWidget(preview_card)
        outer.addStretch(1)

        self.refresh_user_lists()

    # --- helpers ---

    def _set_placeholder(self, text='No preview'):
        img = create_placeholder_image((620, 280), text=text)
        self.thumbnail_label.setPixmap(pil_to_qpixmap(img).scaledToWidth(620, Qt.SmoothTransformation))

    def _on_mode_changed(self, idx):
        self.input_stack.setCurrentIndex(idx)

    def _browse_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, 'Select links file', '', 'Links files (*.json *.txt);;All files (*)'
        )
        if f:
            self.file_entry.setText(f)

    def get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def refresh_user_lists(self):
        self.userlist_dropdown.clear()
        links_path = os.path.join(self.get_base_path(), 'links')
        if os.path.isdir(links_path):
            json_files = [f for f in os.listdir(links_path) if f.endswith('.json')]
            self.userlist_dropdown.addItems(json_files)

    def _on_download_clicked(self):
        idx = self.mode_dropdown.currentIndex()
        if idx == 0:
            value = self.url_entry.text().strip()
        elif idx == 1:
            sel = self.userlist_dropdown.currentText()
            if not sel:
                QMessageBox.information(self, 'No user list', 'Create a user list first under "User Lists".')
                return
            value = os.path.join(self.get_base_path(), 'links', sel)
        else:
            value = self.file_entry.text().strip()
        if not value:
            QMessageBox.warning(self, 'Missing input', 'Please enter a URL or pick a file.')
            return
        self.queue_requested.emit(value)

    def fetch_image(self):
        url = self.url_entry.text()
        if not url:
            self._set_placeholder()
            return
        try:
            id = url.split('-')[-1]
            main_data = requests.get(f'https://sketchfab.com/i/models/{id}').json()
            imgurl = main_data['thumbnails']['images'][0]['url']
            response = requests.get(imgurl)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            img.thumbnail((640, 360))
            pix = pil_to_qpixmap(img)
            self.thumbnail_label.setPixmap(pix)
        except Exception:
            self._set_placeholder('Image not found')
subprocess.run(binz_osg, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


class QueuePage(QWidget):
    """Vertical list of QueueItemCards. The MainWindow drives the queue."""

    cancel_item = Signal(object)
    remove_item = Signal(object)
    clear_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel('Queue')
        title.setObjectName('PageTitle')
        title_box.addWidget(title)
        sub = QLabel('Active and recent downloads.')
        sub.setObjectName('PageSubtitle')
        title_box.addWidget(sub)
        header.addLayout(title_box, 1)

        clear_btn = QPushButton('Clear finished')
        clear_btn.clicked.connect(self.clear_finished.emit)
        header.addWidget(clear_btn, 0, Qt.AlignBottom)
        outer.addLayout(header)

        # Scrollable list of cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_holder = QWidget()
        self.list_layout = QVBoxLayout(self.list_holder)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)

        self.empty_label = QLabel("Nothing in the queue yet.\nAdd a model from the Download page.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #8e8e93; font-size: 13px; padding: 60px 0;")
        self.list_layout.addWidget(self.empty_label)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_holder)
        outer.addWidget(self.scroll, 1)

    def add_card(self, card: QueueItemCard):
        self.empty_label.hide()
        self.list_layout.insertWidget(self.list_layout.count() - 1, card)
        card.cancel_requested.connect(self.cancel_item.emit)
        card.remove_requested.connect(self.remove_item.emit)

    def remove_card(self, card: QueueItemCard):
        card.setParent(None)
        card.deleteLater()
        # Show empty state if no cards remain.
        # count() includes the stretch + (maybe) empty_label; check for any QueueItemCard child.
        any_card = any(
            isinstance(self.list_layout.itemAt(i).widget(), QueueItemCard)
            for i in range(self.list_layout.count())
        )
        if not any_card:
            self.empty_label.show()


class UserListsPage(QWidget):
    list_created = Signal()  # so DownloadPage can refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel('User Lists')
        title.setObjectName('PageTitle')
        outer.addWidget(title)

        sub = QLabel('Save the model list of any Sketchfab user to download later.')
        sub.setObjectName('PageSubtitle')
        outer.addWidget(sub)

        # Create form card
        create_card = make_card()
        cl = QVBoxLayout(create_card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(10)

        section = QLabel('Create a new list')
        section.setObjectName('SectionLabel')
        cl.addWidget(section)

        row = QHBoxLayout()
        self.user_entry = QLineEdit()
        self.user_entry.setPlaceholderText('https://sketchfab.com/<username>')
        row.addWidget(self.user_entry, 1)
        self.create_btn = QPushButton('Create List')
        self.create_btn.setObjectName('Primary')
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.create_list)
        row.addWidget(self.create_btn)
        cl.addLayout(row)

        self.create_status = QLabel('')
        self.create_status.setObjectName('Hint')
        cl.addWidget(self.create_status)

        outer.addWidget(create_card)

        # Existing lists card
        list_card = make_card()
        ll = QVBoxLayout(list_card)
        ll.setContentsMargins(20, 18, 20, 18)
        ll.setSpacing(10)

        head_row = QHBoxLayout()
        sec = QLabel('Saved lists')
        sec.setObjectName('SectionLabel')
        head_row.addWidget(sec, 1)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh)
        head_row.addWidget(refresh)
        ll.addLayout(head_row)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget::item { padding: 8px 10px; background: #f5f5f7; "
            "border-radius: 6px; margin-bottom: 4px; } "
            "QListWidget::item:selected { background: #cfe5ff; color: #1d1d1f; }"
        )
        ll.addWidget(self.list_widget)

        outer.addWidget(list_card, 1)

        self.refresh()

    def get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def refresh(self):
        self.list_widget.clear()
        links_path = os.path.join(self.get_base_path(), 'links')
        if os.path.isdir(links_path):
            for f in sorted(os.listdir(links_path)):
                if f.endswith('.json'):
                    full = os.path.join(links_path, f)
                    try:
                        with open(full) as fh:
                            count = len(json.load(fh))
                        self.list_widget.addItem(f'{f}    —    {count} models')
                    except Exception:
                        self.list_widget.addItem(f)

    def create_list(self):
        user = self.user_entry.text().strip()
        if not user:
            self.create_status.setText('Please enter a user URL.')
            return

        self.create_btn.setEnabled(False)
        self.create_status.setText('Fetching…')
        QApplication.processEvents()

        base_path = self.get_base_path()
        links_path = os.path.join(base_path, 'links')
        os.makedirs(links_path, exist_ok=True)
        file_name = user.split('/')[-1] + '.json'

        try:
            page_text = requests.get(user).text
            line_to_find = 'data-profile-user=\"'
            user_id = page_text.split(line_to_find)[1].split('\">')[0]
            user_json_link = f'https://sketchfab.com/i/models?restricted=1&sort_by=-publishedAt&user={user_id}'
            user_json = requests.get(user_json_link).json()
            modellinks = []

            def write_links(uj):
                for i in uj['results']:
                    if i['isPublished'] and i['visibility'] == 'public' and (i['viewerUrl'] not in modellinks):
                        modellinks.append(i['viewerUrl'])

            write_links(user_json)

            def next_page(uj):
                if uj['next'] is not None:
                    new_json = requests.get(uj['next']).json()
                    write_links(new_json)
                    next_page(new_json)
                else:
                    with open(os.path.join(links_path, file_name), 'w') as x:
                        json.dump(modellinks, x, indent=4)

            next_page(user_json)
            self.create_status.setText(f'{len(modellinks)} models saved to {file_name}')
            self.user_entry.clear()
            self.refresh()
            self.list_created.emit()
        except Exception as e:
            self.create_status.setText(f'Error: {e}')
        finally:
            self.create_btn.setEnabled(True)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel('Settings')
        title.setObjectName('PageTitle')
        outer.addWidget(title)

        sub = QLabel('Configure paths, exports, and advanced options.')
        sub.setObjectName('PageSubtitle')
        outer.addWidget(sub)

        # --- Paths card ---
        paths_card = make_card()
        pl = QVBoxLayout(paths_card)
        pl.setContentsMargins(20, 18, 20, 18)
        pl.setSpacing(12)

        sec1 = QLabel('Paths')
        sec1.setObjectName('SectionLabel')
        pl.addWidget(sec1)

        self.blender_entry = QLineEdit(blender_path)
        self.blender_entry.setPlaceholderText('Folder containing blender.exe')
        pl.addLayout(self._field_with_browse('Blender folder', self.blender_entry, self._select_blender_path))

        self.custom_folder_entry = QLineEdit(custom_download_folder)
        self.custom_folder_entry.setPlaceholderText('Leave empty to use ./downloads')
        pl.addLayout(self._field_with_browse('Download folder', self.custom_folder_entry, self._select_download_folder))

        outer.addWidget(paths_card)

        # --- Export card ---
        export_card = make_card()
        el = QVBoxLayout(export_card)
        el.setContentsMargins(20, 18, 20, 18)
        el.setSpacing(10)

        sec2 = QLabel('Export')
        sec2.setObjectName('SectionLabel')
        el.addWidget(sec2)

        self.fbx_checkbox = QCheckBox('FBX Export')
        self.fbx_checkbox.setChecked(fbx_export)
        el.addWidget(self.fbx_checkbox)

        self.thumbnail_checkbox = QCheckBox('Download thumbnail')
        self.thumbnail_checkbox.setChecked(thumbnail_download)
        el.addWidget(self.thumbnail_checkbox)

        # STL row + size
        self.stl_checkbox = QCheckBox('STL Export')
        stl_export_val = config.get('Paths', 'stl_export', fallback='false').lower() == 'true'
        self.stl_checkbox.setChecked(stl_export_val)
        el.addWidget(self.stl_checkbox)

        stl_hint = QLabel('STL export requires a configured Blender folder.')
        stl_hint.setObjectName('Hint')
        el.addWidget(stl_hint)

        self.stl_size_row = QWidget()
        ss = QHBoxLayout(self.stl_size_row)
        ss.setContentsMargins(24, 0, 0, 0)
        ss.setSpacing(8)
        ss.addWidget(QLabel('Max STL size (mm):'))
        self.stl_size_input = QLineEdit(str(config.get('Paths', 'stl_size', fallback='100')))
        self.stl_size_input.setFixedWidth(80)
        ss.addWidget(self.stl_size_input)
        ss.addStretch(1)
        el.addWidget(self.stl_size_row)

        self.stl_size_row.setVisible(self.stl_checkbox.isChecked())
        self.stl_checkbox.stateChanged.connect(
            lambda s: self.stl_size_row.setVisible(bool(s))
        )

        outer.addWidget(export_card)

        # --- Advanced card ---
        adv_card = make_card()
        al = QVBoxLayout(adv_card)
        al.setContentsMargins(20, 18, 20, 18)
        al.setSpacing(10)

        sec3 = QLabel('Advanced')
        sec3.setObjectName('SectionLabel')
        al.addWidget(sec3)

        self.quads_checkbox = QCheckBox('Quads recreation (experimental)')
        self.quads_checkbox.setChecked(quads_recreation)
        al.addWidget(self.quads_checkbox)

        adv_hint = QLabel('Tries to merge triangles back into quads when ≥75% of the mesh is quads.')
        adv_hint.setObjectName('Hint')
        al.addWidget(adv_hint)

        outer.addWidget(adv_card)

        outer.addStretch(1)

        # --- Save bar ---
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_status = QLabel('')
        self.save_status.setObjectName('Hint')
        save_row.addWidget(self.save_status)
        save_row.addSpacing(10)
        save_btn = QPushButton('Save')
        save_btn.setObjectName('Primary')
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_settings)
        save_row.addWidget(save_btn)
        outer.addLayout(save_row)

    def _field_with_browse(self, label_text, line_edit, browse_fn):
        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)
        lab = QLabel(label_text)
        lab.setObjectName('FieldLabel')
        wrapper.addWidget(lab)

        row = QHBoxLayout()
        row.addWidget(line_edit, 1)
        b = QPushButton('Browse…')
        b.clicked.connect(browse_fn)
        row.addWidget(b)
        wrapper.addLayout(row)
        return wrapper

    def _select_blender_path(self):
        f = QFileDialog.getExistingDirectory(self, 'Select Blender Folder')
        if f:
            self.blender_entry.setText(f)

    def _select_download_folder(self):
        f = QFileDialog.getExistingDirectory(self, 'Select Download Folder')
        if f:
            self.custom_folder_entry.setText(f)

    def save_settings(self):
        global thumbnail_download
        global blender_path
        global fbx_export
        global quads_recreation
        global custom_download_folder

        if not config.has_section('Paths'):
            config.add_section('Paths')
        config.set('Paths', 'blender', self.blender_entry.text())
        config.set('Paths', 'custom_download_folder', self.custom_folder_entry.text())
        config.set('Paths', 'fbx_export', 'true' if self.fbx_checkbox.isChecked() else 'false')
        config.set('Paths', 'thumbnail_download', 'true' if self.thumbnail_checkbox.isChecked() else 'false')
        config.set('Paths', 'quads_recreation', 'true' if self.quads_checkbox.isChecked() else 'false')
        config.set('Paths', 'stl_export', 'true' if self.stl_checkbox.isChecked() else 'false')

        if self.stl_checkbox.isChecked():
            stl_size_val = self.stl_size_input.text()
            try:
                float(stl_size_val)
            except ValueError:
                stl_size_val = '100'
            config.set('Paths', 'stl_size', stl_size_val)
        else:
            config.set('Paths', 'stl_size', '100')

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

        blender_path = self.blender_entry.text()
        custom_download_folder = self.custom_folder_entry.text()
        fbx_export = self.fbx_checkbox.isChecked()
        thumbnail_download = self.thumbnail_checkbox.isChecked()
        quads_recreation = self.quads_checkbox.isChecked()

        self.save_status.setText('Saved ✓')
        QTimer.singleShot(2500, lambda: self.save_status.setText(''))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('Root')
        self.setWindowTitle('Sketchfab v2.5')
        self.resize(980, 720)

        self.queue = []
        self.current_thread = None
        self.current_card = None

        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.nav_changed.connect(self._on_nav)
        root.addWidget(self.sidebar)

        # Stacked pages
        self.pages = QStackedWidget()

        self.download_page = DownloadPage()
        self.queue_page = QueuePage()
        self.userlists_page = UserListsPage()
        self.settings_page = SettingsPage()

        self.pages.addWidget(self.download_page)
        self.pages.addWidget(self.queue_page)
        self.pages.addWidget(self.userlists_page)
        self.pages.addWidget(self.settings_page)

        root.addWidget(self.pages, 1)

        # Wire signals
        self.download_page.queue_requested.connect(self._enqueue)
        self.queue_page.cancel_item.connect(self._cancel_item)
        self.queue_page.remove_item.connect(self._remove_item)
        self.queue_page.clear_finished.connect(self._clear_finished)
        self.userlists_page.list_created.connect(self.download_page.refresh_user_lists)

    # --- Navigation ---

    def _on_nav(self, idx):
        self.pages.setCurrentIndex(idx)
        if idx == 0:
            self.download_page.refresh_user_lists()
        elif idx == 2:
            self.userlists_page.refresh()

    # --- Queue management ---

    def _enqueue(self, source):
        card = QueueItemCard(source)
        self.queue.append(card)
        self.queue_page.add_card(card)

        # Switch to the queue page so the user sees their addition.
        self.sidebar.buttons[1].click()
        self._maybe_start_next()

    def _maybe_start_next(self):
        if self.current_thread is not None:
            return
        # Find first queued card.
        next_card = next((c for c in self.queue if c.status == STATUS_QUEUED), None)
        if next_card is None:
            return

        self.current_card = next_card
        next_card.set_status(STATUS_RUNNING)
        next_card.set_text('Starting…')
        next_card.set_progress(0)

        thread = DownloadThread(next_card.source)
        thread.progress_signal.connect(next_card.set_progress)
        thread.text_signal.connect(next_card.set_text)
        thread.finished_signal.connect(self._on_thread_finished)
        self.current_thread = thread
        thread.start()

    def _on_thread_finished(self):
        if self.current_card is not None:
            # If status_text says "cancelled" we honor that; otherwise mark done.
            if self.current_card.status == STATUS_RUNNING:
                if self.current_card.progress.value() >= 100:
                    self.current_card.set_status(STATUS_DONE)
                else:
                    # Could be a per-link multi-download finishing; treat as done.
                    self.current_card.set_status(STATUS_DONE)

        self.current_thread = None
        self.current_card = None
        self._maybe_start_next()

    def _cancel_item(self, card):
        if card is self.current_card and self.current_thread is not None:
            self.current_thread.cancel()
            card.set_status(STATUS_CANCELLED)
        else:
            # Just-queued item — mark cancelled and leave it for removal.
            card.set_status(STATUS_CANCELLED)

    def _remove_item(self, card):
        if card in self.queue:
            self.queue.remove(card)
        self.queue_page.remove_card(card)

    def _clear_finished(self):
        terminal = (STATUS_DONE, STATUS_FAILED, STATUS_CANCELLED)
        for card in list(self.queue):
            if card.status in terminal:
                self.queue.remove(card)
                self.queue_page.remove_card(card)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(QIcon(resource_path('logo.ico')))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())