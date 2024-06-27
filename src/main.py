import sys
import ctypes.util
from dragiyski.vulkan.implementation import *

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
        print(' - %s [%s]' % (extension, extension.spec_version))
    return 0


if __name__ == '__main__':
    sys.exit(main())
