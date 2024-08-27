from types import SimpleNamespace
import ctypes.util, sys, pathlib
import functools, operator
from dragiyski.vulkan import binding, loader as vulkan_loader
from dragiyski.vulkan.version import VkVersion, VkApiVersion

log = functools.partial(print, file=sys.stderr)

def get_address(dll, name):
    return ctypes.cast(getattr(dll, name), ctypes.c_void_p).value

def append_struct_chain(source, target):
    last = ctypes.cast(ctypes.c_void_p(ctypes.addressof(source)), ctypes.POINTER(binding.VkBaseInStructure)).contents
    target = ctypes.cast(ctypes.c_void_p(ctypes.addressof(target)), ctypes.POINTER(binding.VkBaseInStructure))
    while last.pNext:
        last = last.pNext.contents
    last.pNext = target

def debug_utils_callback(
    severity: binding.VkDebugUtilsMessageSeverityFlagsEXT,
    type: binding.VkDebugUtilsMessageTypeFlagsEXT,
    data: ctypes.POINTER(binding.VkDebugUtilsMessengerCallbackDataEXT), # type: ignore
    user_data: ctypes.c_void_p
):
    log('vulkan.debug: %s' % data.contents.pMessage.decode())
    return binding.VK_FALSE

def debug_report_callback(
    flags: binding.VkDebugReportFlagsEXT,
    objectType: binding.VkDebugReportObjectTypeEXT,
    object: int,
    location: int,
    messageCode: int,
    pLayerPrefix: bytes,
    pMessage: bytes,
    pUserData: ctypes.c_void_p
):
    log('vulkan.debug: %s' % pMessage.decode())
    return binding.VK_FALSE

debug_utils_callback_ptr = binding.vkDebugUtilsMessengerCallbackEXT(debug_utils_callback)
debug_report_callback_ptr = binding.vkDebugReportCallbackEXT(debug_report_callback)

def main():
    library_loader = vulkan_loader.LibraryLoader()
    
    version = library_loader.vkEnumerateInstanceVersion.argtypes[0]._type_(0)
    result = library_loader.vkEnumerateInstanceVersion(ctypes.byref(version))
    if result != binding.VkResult.VK_SUCCESS:
        raise RuntimeError(binding.VkResult(result).name)
    version = VkApiVersion(version.value)
    log('vulkan.version = %s' % (version))
    
    layer_count = library_loader.vkEnumerateInstanceLayerProperties.argtypes[0]._type_(0)
    result = library_loader.vkEnumerateInstanceLayerProperties(ctypes.byref(layer_count), None)
    if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
        raise RuntimeError(binding.VkResult(result).name)
    while layer_count.value > 0:
        layer_array = (binding.VkLayerProperties * layer_count.value)()
        result = library_loader.vkEnumerateInstanceLayerProperties(ctypes.byref(layer_count), ctypes.cast(layer_array, library_loader.vkEnumerateInstanceLayerProperties.argtypes[1]))
        if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
            raise RuntimeError(binding.VkResult(result).name)
        if layer_count.value > len(layer_array):
            continue
        break
    layers = {x.layerName.decode() for x in layer_array} if layer_count.value > 0 else set()
    if layer_count.value > 0:
        log('vulkan.layers:')
        for layer_properties in layer_array:
            log(' - %s:' % layer_properties.layerName.decode())
            log('    spec_version: %s' % VkApiVersion(layer_properties.specVersion))
            log('    implementation_version: %d' % layer_properties.implementationVersion)
            log('    description: %s' % layer_properties.description.decode())

    extension_count = library_loader.vkEnumerateInstanceExtensionProperties.argtypes[1]._type_(0)
    result = library_loader.vkEnumerateInstanceExtensionProperties(None, ctypes.byref(extension_count), None)
    if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
        raise RuntimeError(binding.VkResult(result).name)
    while extension_count.value > 0:
        extension_array = (binding.VkExtensionProperties * extension_count.value)()
        result = library_loader.vkEnumerateInstanceExtensionProperties(None, ctypes.byref(extension_count), ctypes.cast(extension_array, library_loader.vkEnumerateInstanceExtensionProperties.argtypes[2]))
        if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
            raise RuntimeError(binding.VkResult(result).name)
        if extension_count.value > len(extension_array):
            continue
        break
    extensions = {x.extensionName.decode() for x in extension_array} if extension_count.value > 0 else set()
    if extension_count.value > 0:
        log('vulkan.extensions:')
        for extension_properties in extension_array:
            log(' - %s' % extension_properties.extensionName.decode())

    enabled_layers = set()
    enabled_extensions = set()

    if 'VK_LAYER_KHRONOS_validation' in layers:
        enabled_layers.add('VK_LAYER_KHRONOS_validation')
        extension_count = library_loader.vkEnumerateInstanceExtensionProperties.argtypes[1]._type_(0)
        result = library_loader.vkEnumerateInstanceExtensionProperties(b'VK_LAYER_KHRONOS_validation', ctypes.byref(extension_count), None)
        if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
            raise RuntimeError(binding.VkResult(result).name)
        while extension_count.value > 0:
            extension_array = (binding.VkExtensionProperties * extension_count.value)()
            result = library_loader.vkEnumerateInstanceExtensionProperties(b'VK_LAYER_KHRONOS_validation', ctypes.byref(extension_count), ctypes.cast(extension_array, library_loader.vkEnumerateInstanceExtensionProperties.argtypes[2]))
            if result not in [binding.VkResult.VK_SUCCESS, binding.VkResult.VK_INCOMPLETE]:
                raise RuntimeError(binding.VkResult(result).name)
            if extension_count.value > len(extension_array):
                continue
            break
        extensions = extensions.union({x.extensionName.decode() for x in extension_array} if extension_count.value > 0 else set())
        if extension_count.value > 0:
            log('vulkan.extensions[%s]:' % 'VK_LAYER_KHRONOS_validation')
            for extension_properties in extension_array:
                log(' - %s' % extension_properties.extensionName.decode())
        
    if 'VK_EXT_debug_utils' in extensions:
        enabled_extensions.add('VK_EXT_debug_utils')
    elif 'VK_EXT_debug_report' in extensions:
        enabled_extensions.add('VK_EXT_debug_report')
    
    if 'VK_EXT_layer_settings' in extensions:
        enabled_extensions.add('VK_EXT_layer_settings')
    elif 'VK_EXT_validation_features' in extensions:
        enabled_extensions.add('VK_EXT_validation_features')

    create_info = binding.VkInstanceCreateInfo(sType = binding.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO)
    application_info = binding.VkApplicationInfo(sType = binding.VK_STRUCTURE_TYPE_APPLICATION_INFO)
    application_info.pApplicationName = b'gray'
    application_info.applicationVersion = 1
    application_info.pEngineName = b'python'
    application_info.engineVersion = VkApiVersion.create(major=sys.version_info.major, minor=sys.version_info.minor, patch=sys.version_info.micro)
    application_info.apiVersion = version
    create_info.pApplicationInfo = ctypes.pointer(application_info)
    enabled_layers_array = (ctypes.c_char_p * len(enabled_layers))(*[x.encode() for x in enabled_layers]) if len(enabled_layers) > 0 else None
    enabled_extensions_array = (ctypes.c_char_p * len(enabled_extensions))(*[x.encode() for x in enabled_extensions]) if len(enabled_extensions) > 0 else None
    create_info.enabledLayerCount = len(enabled_layers)
    create_info.ppEnabledLayerNames = enabled_layers_array
    create_info.enabledExtensionCount = len(enabled_extensions)
    create_info.ppEnabledExtensionNames = enabled_extensions_array

    if 'VK_EXT_debug_utils' in enabled_extensions:
        debug_message_create_info = binding.VkDebugUtilsMessengerCreateInfoEXT(sType=binding.VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT)
        debug_message_create_info.flags = 0
        debug_message_create_info.messageSeverity = functools.reduce(operator.or_, binding.VkDebugUtilsMessageSeverityFlagsEXT)
        debug_message_create_info.messageType = functools.reduce(operator.or_, binding.VkDebugUtilsMessageTypeFlagsEXT)
        debug_message_create_info.pfnUserCallback = debug_utils_callback_ptr
        debug_message_create_info.pUserData = None
        append_struct_chain(create_info, debug_message_create_info)
    if 'VK_EXT_debug_report' in enabled_extensions:
        debug_report_create_info = binding.VkDebugReportCallbackCreateInfoEXT(sType=binding.VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT)
        debug_report_create_info.flags = functools.reduce(operator.or_, binding.VkDebugReportFlagsEXT)
        debug_report_create_info.pfnCallback = debug_report_callback_ptr
        debug_report_create_info.pUserData = None
        append_struct_chain(create_info, debug_report_create_info)
    if 'VK_EXT_validation_features' in enabled_extensions:
        validation_features = binding.VkValidationFeaturesEXT(sType=binding.VK_STRUCTURE_TYPE_VALIDATION_FEATURES_EXT)
        enabled_validation_features = [
            binding.VkValidationFeatureEnableEXT.VK_VALIDATION_FEATURE_ENABLE_GPU_ASSISTED_EXT,
            binding.VkValidationFeatureEnableEXT.VK_VALIDATION_FEATURE_ENABLE_GPU_ASSISTED_RESERVE_BINDING_SLOT_EXT,
            binding.VkValidationFeatureEnableEXT.VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT,
            binding.VkValidationFeatureEnableEXT.VK_VALIDATION_FEATURE_ENABLE_BEST_PRACTICES_EXT,
        ]
        validation_features.enabledValidationFeatureCount = len(enabled_validation_features)
        validation_features.pEnabledValidationFeatures = (validation_features.pEnabledValidationFeatures._type_ * len(enabled_validation_features))(*enabled_validation_features)
        validation_features.disabledValidationFeatureCount = 0
        validation_features.pDisabledValidationFeatures = None
        append_struct_chain(create_info, validation_features)
        del enabled_validation_features
    # if 'VK_EXT_layer_settings' in enabled_extensions:
    #     layer_settings = binding.VkLayerSettingsCreateInfoEXT(sType=binding.VK_STRUCTURE_TYPE_LAYER_SETTINGS_CREATE_INFO_EXT)
    #     binding.VK_VALIDATION_FEATURE_ENABLE_GPU_ASSISTED_EXT
    #     enabled_layer_settings = [
    #         binding.VkLayerSettingEXT(
    #             pLayerName=b'khronos_validation',
    #             pSettingName=b'validate_gpu_based',

    #         )
    #     ]

    instance = binding.vkCreateInstance._argtypes_[2]._type_()
    result = library_loader.vkCreateInstance(ctypes.byref(create_info), None, ctypes.byref(instance))
    if result != binding.VK_SUCCESS:
        raise RuntimeError(binding.VkResult(result).name)
    instance_loader = vulkan_loader.InstanceLoader(library_loader, instance)

    instance_loader.vkDestroyInstance(instance, None)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
