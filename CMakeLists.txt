cmake_minimum_required(VERSION 3.24)
project(noveltea_shaderc_toolchain LANGUAGES C CXX)

# Permit compilation fan-out while preventing several large static archives from
# linking concurrently on constrained release runners.
set(CMAKE_JOB_POOLS link_pool=1)
set(CMAKE_JOB_POOL_LINK link_pool)

include(FetchContent)
include(cmake/noveltea_bgfx_version.cmake)

# The embedded archives must remain suitable for linking into NovelTea's shared CLI.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(BGFX_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BGFX_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(BGFX_INSTALL OFF CACHE BOOL "" FORCE)
set(BGFX_BUILD_TOOLS ON CACHE BOOL "" FORCE)
set(BGFX_BUILD_TOOLS_BIN2C OFF CACHE BOOL "" FORCE)
set(BGFX_BUILD_TOOLS_GEOMETRY OFF CACHE BOOL "" FORCE)
set(BGFX_BUILD_TOOLS_TEXTURE ON CACHE BOOL "" FORCE)
set(BGFX_BUILD_TOOLS_SHADER ON CACHE BOOL "" FORCE)
set(BGFX_CUSTOM_TARGETS OFF CACHE BOOL "" FORCE)
set(BGFX_CONFIG_MULTITHREADED OFF CACHE BOOL "" FORCE)

FetchContent_Declare(noveltea_shaderc_bgfx
    URL "${NOVELTEA_SHADERC_BGFX_ARCHIVE_URL}"
    URL_HASH "SHA256=${NOVELTEA_SHADERC_BGFX_ARCHIVE_SHA256}"
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(noveltea_shaderc_bgfx)

if(NOT TARGET shaderc)
    message(FATAL_ERROR "Pinned bgfx source did not define its shaderc target")
endif()
if(NOT TARGET texturec)
    message(FATAL_ERROR "Pinned bgfx source did not define its texturec target")
endif()

# Walk the actual target graph exported by this bgfx.cmake release.  In particular,
# current shaderc includes Tint; keeping this derived avoids silently dropping new
# static dependencies when bgfx changes its tool closure.
macro(noveltea_collect_static_closure target)
    if(TARGET "${target}")
        get_target_property(_noveltea_type "${target}" TYPE)
        if(_noveltea_type STREQUAL "STATIC_LIBRARY")
            list(FIND NOVELTEA_CLOSURE_TARGETS "${target}" _noveltea_seen)
            if(_noveltea_seen EQUAL -1)
                list(APPEND NOVELTEA_CLOSURE_TARGETS "${target}")
            endif()
        endif()
        get_target_property(_noveltea_links "${target}" LINK_LIBRARIES)
        get_target_property(_noveltea_interface_links "${target}" INTERFACE_LINK_LIBRARIES)
        foreach(_noveltea_link IN LISTS _noveltea_links _noveltea_interface_links)
            if(TARGET "${_noveltea_link}")
                noveltea_collect_static_closure("${_noveltea_link}")
            endif()
        endforeach()
    endif()
endmacro()

get_target_property(NOVELTEA_SHADERC_SOURCES shaderc SOURCES)
get_target_property(NOVELTEA_SHADERC_LINKS shaderc LINK_LIBRARIES)
get_target_property(NOVELTEA_TEXTUREC_SOURCES texturec SOURCES)
get_target_property(NOVELTEA_TEXTUREC_LINKS texturec LINK_LIBRARIES)
if(NOT NOVELTEA_SHADERC_SOURCES OR NOT NOVELTEA_SHADERC_LINKS
   OR NOT NOVELTEA_TEXTUREC_SOURCES OR NOT NOVELTEA_TEXTUREC_LINKS)
    message(FATAL_ERROR "Pinned bgfx tool targets did not expose their source/link closures")
endif()

set(NOVELTEA_CLOSURE_TARGETS)
foreach(noveltea_link IN LISTS NOVELTEA_SHADERC_LINKS NOVELTEA_TEXTUREC_LINKS)
    noveltea_collect_static_closure("${noveltea_link}")
endforeach()

add_library(noveltea_bgfx_shaderc_embedded STATIC ${NOVELTEA_SHADERC_SOURCES})
set_target_properties(noveltea_bgfx_shaderc_embedded PROPERTIES
    POSITION_INDEPENDENT_CODE ON CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
target_compile_definitions(noveltea_bgfx_shaderc_embedded PRIVATE
    main=noveltea_bgfx_shaderc_embedded_cli_main)
target_link_libraries(noveltea_bgfx_shaderc_embedded PUBLIC ${NOVELTEA_SHADERC_LINKS})
target_include_directories(noveltea_bgfx_shaderc_embedded PUBLIC
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/tools/shaderc>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bx/include>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/dawn>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/dawn/src>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-headers/include>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-tools>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-tools/include>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-tools/include/generated>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/directx-headers/include/directx>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/directx-headers/include>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/directx-headers/include/wsl/stubs>")

get_target_property(NOVELTEA_TEXTUREC_SOURCES texturec SOURCES)
get_target_property(NOVELTEA_TEXTUREC_LINKS texturec LINK_LIBRARIES)
if(NOT NOVELTEA_TEXTUREC_SOURCES OR NOT NOVELTEA_TEXTUREC_LINKS)
    message(FATAL_ERROR "Pinned bgfx texturec target did not expose its source/link closure")
endif()

add_library(noveltea_bimg_texturec_embedded STATIC ${NOVELTEA_TEXTUREC_SOURCES})
set_target_properties(noveltea_bimg_texturec_embedded PROPERTIES
    POSITION_INDEPENDENT_CODE ON CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
target_compile_definitions(noveltea_bimg_texturec_embedded PRIVATE
    main=noveltea_bimg_texturec_main)
target_link_libraries(noveltea_bimg_texturec_embedded PUBLIC ${NOVELTEA_TEXTUREC_LINKS})

# Record the two graph projections for the generated import file, while keeping
# one deduplicated archive install list for the package.
set(NOVELTEA_SHADERC_LINK_TARGETS)
foreach(noveltea_link IN LISTS NOVELTEA_SHADERC_LINKS)
    if(TARGET "${noveltea_link}")
        get_target_property(_noveltea_type "${noveltea_link}" TYPE)
        if(_noveltea_type STREQUAL "STATIC_LIBRARY")
            list(APPEND NOVELTEA_SHADERC_LINK_TARGETS "${noveltea_link}")
        endif()
    endif()
endforeach()
set(NOVELTEA_TEXTUREC_LINK_TARGETS)
foreach(noveltea_link IN LISTS NOVELTEA_TEXTUREC_LINKS)
    if(TARGET "${noveltea_link}")
        get_target_property(_noveltea_type "${noveltea_link}" TYPE)
        if(_noveltea_type STREQUAL "STATIC_LIBRARY")
            list(APPEND NOVELTEA_TEXTUREC_LINK_TARGETS "${noveltea_link}")
        endif()
    endif()
endforeach()

set(NOVELTEA_IMPORTED_ARCHIVES)
foreach(noveltea_dependency IN LISTS NOVELTEA_CLOSURE_TARGETS)
    get_target_property(_noveltea_output "${noveltea_dependency}" OUTPUT_NAME)
    if(NOT _noveltea_output OR _noveltea_output STREQUAL "_noveltea_output-NOTFOUND")
        set(_noveltea_output "${noveltea_dependency}")
    endif()
    list(APPEND NOVELTEA_IMPORTED_ARCHIVES "${noveltea_dependency}|lib${_noveltea_output}.a")
endforeach()

add_custom_target(noveltea_shaderc_bundle ALL DEPENDS
    noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded ${NOVELTEA_CLOSURE_TARGETS})

install(TARGETS noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded
    ${NOVELTEA_CLOSURE_TARGETS} ARCHIVE DESTINATION lib)
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/tools/shaderc/"
    DESTINATION include/bgfx/tools/shaderc FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/"
    DESTINATION include/bgfx/src FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bx/include/"
    DESTINATION include/bx FILES_MATCHING
    PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.inl")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/dawn/"
    DESTINATION include/bgfx/3rdparty/dawn FILES_MATCHING
    PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.inc")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-headers/include/"
    DESTINATION include/bgfx/3rdparty/spirv-headers/include FILES_MATCHING PATTERN "*.h")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/3rdparty/spirv-tools/include/"
    DESTINATION include/bgfx/3rdparty/spirv-tools/include FILES_MATCHING PATTERN "*.h")
install(FILES
    "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/bgfx_shader.sh"
    "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/bgfx_compute.sh"
    DESTINATION resources)
configure_file(cmake/noveltea_shaderc_toolchain.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/noveltea_shaderc_toolchain.cmake" @ONLY)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/noveltea_shaderc_toolchain.cmake" DESTINATION cmake)
