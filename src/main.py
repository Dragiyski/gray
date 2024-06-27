import sys
import ctypes.util
import functools
from collections.abc import Mapping
from dragiyski.vulkan.implementation import *

def print_mapping(mapping, indent = 0):
    for name in sorted(mapping):
        if name.startswith('_'):
            continue
        value = mapping[name]
        if isinstance(value, Mapping) and hasattr(value, '_as_parameter_'):
            print('%s%s:' % ('  ' * indent, name))
            print_mapping(mapping[name], indent + 1)
        else:
            print('%s - %s: %r' % ('  ' * indent, name, mapping[name]))

def main():
    app = VulkanApplication()
    print('vk.version: %s' % app.enumerate_instance_version())
    print('vk.layers:')
    for layer in app.enumerate_instance_layer_properties():
        print('  - %s [%s]: %s' % (layer, layer.spec_version, layer.description))
    print('vk.extensions:')
    for extension in app.enumerate_instance_extension_properties():
        print(' - %s [%s]' % (extension, extension.spec_version))
    instance = VkInstance.create(
        app,
        required_extensions = ['VK_EXT_debug_utils'],
        application_info = VkApplicationInfo(
            api_version = app.enumerate_instance_version()
        )
    )
    print('vkCreateInstance(0x%016x)' % instance._as_parameter_)
    selected_physical_device = None
    physical_device = instance.enumerate_physical_devices()
    physical_device_properties = list(dev.get_properties() for dev in physical_device)
    for index, properties in enumerate(physical_device_properties):
        if properties.device_type == VkPhysicalDeviceType.VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU:
            selected_physical_device = index
    if selected_physical_device is None:
        for index, properties in enumerate(physical_device_properties):
            if properties.device_type == VkPhysicalDeviceType.VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU:
                selected_physical_device = index
    if selected_physical_device is None:
        raise RuntimeError('Unable to find GPU physical device')
    physical_device = physical_device[selected_physical_device]
    physical_device_properties = physical_device_properties[selected_physical_device]
    physical_device_family_queue_properties = physical_device.get_family_queue_properties()
    physical_device_layers = physical_device.enumerate_device_layer_properties()
    physical_device_extensions = physical_device.enumerate_device_extension_properties()
    print('device: %s [%s]' % (physical_device_properties.device_name, physical_device_properties.api_version))
    print('  device.layers:')
    for layer in physical_device_layers:
        print('   - %s [%s]: %s' % (layer, layer.spec_version, layer.description))
    print('  device.extensions:')
    for extension in physical_device_extensions:
        print('   - %s [%s]' % (extension, extension.spec_version))
    print('  device.properties:')
    print_mapping(physical_device_properties, 2)
    print('  device.family_queue_properties:')
    for i, p in enumerate(physical_device_family_queue_properties):
        print('    %d:' % i)
        print_mapping(p, 3)
    physical_device_family_queue = [i for i, p in enumerate(physical_device_family_queue_properties) if (VK_QUEUE_COMPUTE_BIT | VK_QUEUE_TRANSFER_BIT) in p.queue_flags]
    if len(physical_device_family_queue) <= 0:
        raise RuntimeError('No suitable family queue found in the device. Expected family queue supported VK_QUEUE_COMPUTE_BIT and VK_QUEUE_TRANSFER_BIT')
    physical_device_family_queue = sorted(physical_device_family_queue, key = lambda i: physical_device_family_queue_properties[i].queue_count, reverse = True)
    physical_device_family_queue = physical_device_family_queue[0]
    return 0


if __name__ == '__main__':
    sys.exit(main())
