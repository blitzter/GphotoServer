from __future__ import print_function
from flask import Flask,render_template, Response, send_from_directory, current_app

import logging
import sys, io
import json

import gphoto2 as gp

app = Flask(__name__)
camera = None
context = None
config = None
config_all = {}
camera_config = []
camera_config_name = []

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)
    
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)

@app.route("/")
def index():
    if camera is None:
        test_camera()
    return current_app.send_static_file("index.html")

@app.route("/preview")
def preview():
    if camera is not None:
        return get_preview()
    else:
        return "not found"

@app.route("/config")
def config():
    if config is not None:
        return json.dumps(camera_config)
    else:
        return "not found"

def get_preview():
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    #gp.check_result(gp.use_python_logging())
    #context = gp.gp_context_new()
    #camera = gp.check_result(gp.gp_camera_new())
    #gp.check_result(gp.gp_camera_init(camera, context))
    # required configuration will depend on camera type!
    print('Checking camera config')
    # get configuration tree
    #config = gp.check_result(gp.gp_camera_get_config(camera, context))
    # find the image format config item
    OK, image_format = gp.gp_widget_get_child_by_name(config, 'imageformat')
    if OK >= gp.GP_OK:
        # get current setting
        value = gp.check_result(gp.gp_widget_get_value(image_format))
        # make sure it's not raw
        if 'raw' in value.lower():
            print('Cannot preview raw images')
            return 1
    # find the capture size class config item
    # need to set this on my Canon 350d to get preview to work at all
    OK, capture_size_class = gp.gp_widget_get_child_by_name(
        config, 'capturesizeclass')
    if OK >= gp.GP_OK:
        # set value
        value = gp.check_result(gp.gp_widget_get_choice(capture_size_class, 2))
        gp.check_result(gp.gp_widget_set_value(capture_size_class, value))
        # set config
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
    # capture preview image (not saved to camera memory card)
    print('Capturing preview image')
    camera_file = gp.check_result(gp.gp_camera_capture_preview(camera, context))
    file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
    # display image
    #data = memoryview(file_data)
    #print(type(data), len(data))
    #print(data[:10].tolist())
    gp.check_result(gp.gp_camera_exit(camera, context))
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')

def test_camera():
    global camera, context, config, camera_config_name, camera_config
    print("Testing Camera")
    logging.basicConfig(
        format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    gp.check_result(gp.use_python_logging())
    context = gp.gp_context_new()
    camera_list = []
    for name, addr in context.camera_autodetect():
        camera_list.append((name, addr))
    if not camera_list:
        print('No camera detected')
        return 1
    camera_list.sort(key=lambda x: x[0])
    name, addr = camera_list[0]
    camera = gp.Camera()
    #camera = gp.check_result(gp.gp_camera_new())
    gp.check_result(gp.gp_camera_init(camera, context))
    config = gp.check_result(gp.gp_camera_get_config(camera, context))
    text = gp.check_result(gp.gp_camera_get_summary(camera, context))
    print('Summary')
    print('=======')
    print(text.text)
    print('Abilities')
    print('=========')
    abilities = gp.check_result(gp.gp_camera_get_abilities(camera))
    print('model:', abilities.model)
    print('status:', abilities.status)
    print('port:', abilities.port)
    print('speed:', abilities.speed)
    print('operations:', abilities.operations)
    print('file_operations:', abilities.file_operations)
    print('folder_operations:', abilities.folder_operations)
    print('usb_vendor:', abilities.usb_vendor)
    print('usb_product:', abilities.usb_product)
    print('usb_class:', abilities.usb_class)
    print('usb_subclass:', abilities.usb_subclass)
    print('usb_protocol:', abilities.usb_protocol)
    print('library:', abilities.library)
    print('id:', abilities.id)
    print('device_type:', abilities.device_type)
    child_count = gp.check_result(gp.gp_widget_count_children(config))
    if child_count < 1:
        return
    tabs = None
    for n in range(child_count):
        child = gp.check_result(gp.gp_widget_get_child(config, n))
        camera_config.append(getConfig(child))
        label = gp.check_result(gp.gp_widget_get_label(child))
        camera_config_name.append(label)
        print('!!!!!!! CONFIG ', child, label)
    name = gp.check_result(gp.gp_widget_get_name(child))
    gp.check_result(gp.gp_camera_exit(camera, context))
    return 0

def getConfig(child):
    global config_all
    new_object = {}
    label = gp.check_result(gp.gp_widget_get_label(child))
    name = gp.check_result(gp.gp_widget_get_name(child))
    label = '{} ({})'.format(label, name)
    new_object['name'] = name
    new_object['label'] = label
    config_all[name] = child
    child_type = gp.check_result(gp.gp_widget_get_type(child))
    if child_type == gp.GP_WIDGET_SECTION:
        new_object['type'] = "SECTION"
        new_object['children'] = []
        child_count = gp.check_result(gp.gp_widget_count_children(child))
        for n in range(child_count):
            grand_child = gp.check_result(gp.gp_widget_get_child(child, n))
            new_object['children'].append(getConfig(grand_child))
    elif child_type == gp.GP_WIDGET_TEXT:
        new_object['type'] = "TEXT"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
        value = gp.check_result(gp.gp_widget_get_value(child))
        new_object['value'] = value
    elif child_type == gp.GP_WIDGET_RANGE:
        new_object['type'] = "RANGE"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
        value = gp.check_result(gp.gp_widget_get_value(child))
        new_object['value'] = value
        lo, hi, inc = gp.check_result(gp.gp_widget_get_range(child))
        new_object['low'] = lo
        new_object['high'] = hi
        new_object['increment'] = inc
    elif child_type == gp.GP_WIDGET_TOGGLE:
        new_object['type'] = "TOGGLE"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
        value = gp.check_result(gp.gp_widget_get_value(child))
        new_object['value'] = value
    elif child_type == gp.GP_WIDGET_RADIO:
        new_object['type'] = "RADIO"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
        value = gp.check_result(gp.gp_widget_get_value(child))
        new_object['value'] = value
        choice_count = gp.check_result(gp.gp_widget_count_choices(child))
        new_object['choices'] = []
        for j in range(choice_count):
            choice = gp.check_result(gp.gp_widget_get_choice(child, j))
            if choice:
                new_object['choices'].append(choice)
    elif child_type == gp.GP_WIDGET_MENU:
        new_object['type'] = "MENU"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
    elif child_type == gp.GP_WIDGET_DATE:
        new_object['type'] = "DATE"
        if gp.check_result(gp.gp_widget_get_readonly(child)):
            new_object['disabled'] = True
        value = gp.check_result(gp.gp_widget_get_value(child))
        new_object['value'] = value
    else:
        print('Cannot make widget type %d for %s' % (child_type, label))
    return new_object

@app.route("/status")
def getStatus():
    if camera is not None:
        return "True"
    else:
        return "False"

@app.route("/config/<config_item>/<config_value>")
def setConfig(config_item,config_value):
    child_type = gp.check_result(gp.gp_widget_get_type(config_all[config_item]))
    if child_type == gp.GP_WIDGET_RADIO:
        value = gp.check_result(gp.gp_widget_get_choice(config_all[config_item], int(config_value)))
        gp.check_result(gp.gp_widget_set_value(config_all[config_item],value))
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
    elif child_type == gp.GP_WIDGET_TEXT:
        gp.check_result(gp.gp_widget_set_value(config_all[config_item],config_value))
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
    elif child_type == gp.GP_WIDGET_RANGE:
        gp.check_result(gp.gp_widget_set_value(config_all[config_item],int(config_value)))
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
    elif child_type == gp.GP_WIDGET_TOGGLE:
        value = gp.check_result(gp.gp_widget_get_value(config_all[config_item]))
        if value:
            gp.check_result(gp.gp_widget_set_value(config_all[config_item],0))
        else:
            gp.check_result(gp.gp_widget_set_value(config_all[config_item],1))
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
    return "done"

if __name__ == "__main__":
    test_camera()
    app.run()
