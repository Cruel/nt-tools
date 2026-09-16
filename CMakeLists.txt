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

# Use one standalone miniz provider throughout bimg and TinyEXR. Without an
# explicit dependency, bgfx.cmake compiles the vendored implementation into
# both bimg and bimg_decode while image_decode.cpp includes it a third time.
FetchContent_Declare(noveltea_miniz
    URL "https://github.com/richgel999/miniz/archive/refs/tags/3.1.1.tar.gz"
    URL_HASH "SHA256=8bb29c7bd6f22356e5583e794bed4a0b3e6dfcbcadb49974fc9270ccca1e5557"
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(noveltea_miniz)
if(NOT TARGET miniz)
    message(FATAL_ERROR "Pinned miniz source did not define its miniz target")
endif()
set(MINIZ_LIBRARIES miniz)
get_target_property(MINIZ_INCLUDE_DIR miniz INTERFACE_INCLUDE_DIRECTORIES)

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
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    PATCH_COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/patch-bgfx-miniz.cmake)
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
foreach(noveltea_link IN LISTS NOVELTEA_SHADERC_LINKS)
    noveltea_collect_static_closure("${noveltea_link}")
endforeach()
set(NOVELTEA_SHADERC_CLOSURE_TARGETS ${NOVELTEA_CLOSURE_TARGETS})

set(NOVELTEA_CLOSURE_TARGETS)
foreach(noveltea_link IN LISTS NOVELTEA_TEXTUREC_LINKS)
    noveltea_collect_static_closure("${noveltea_link}")
endforeach()
set(NOVELTEA_TEXTUREC_CLOSURE_TARGETS ${NOVELTEA_CLOSURE_TARGETS})

set(NOVELTEA_CLOSURE_TARGETS
    ${NOVELTEA_SHADERC_CLOSURE_TARGETS}
    ${NOVELTEA_TEXTUREC_CLOSURE_TARGETS})
list(REMOVE_DUPLICATES NOVELTEA_CLOSURE_TARGETS)

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
# Imported archives do not retain the build-tree target graph. Export each
# tool's full static closure so consumers also receive transitive providers
# such as bx and the canonical standalone miniz library.
set(NOVELTEA_SHADERC_LINK_TARGETS ${NOVELTEA_SHADERC_CLOSURE_TARGETS})
set(NOVELTEA_TEXTUREC_LINK_TARGETS ${NOVELTEA_TEXTUREC_CLOSURE_TARGETS})

set(NOVELTEA_IMPORTED_ARCHIVES)
foreach(noveltea_dependency IN LISTS NOVELTEA_CLOSURE_TARGETS)
    get_target_property(_noveltea_output "${noveltea_dependency}" OUTPUT_NAME)
    if(NOT _noveltea_output OR _noveltea_output STREQUAL "_noveltea_output-NOTFOUND")
        set(_noveltea_output "${noveltea_dependency}")
    endif()
    list(APPEND NOVELTEA_IMPORTED_ARCHIVES "${noveltea_dependency}|lib${_noveltea_output}.a")
endforeach()

add_custom_target(noveltea_shaderc_bundle ALL DEPENDS
    shaderc noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded ${NOVELTEA_CLOSURE_TARGETS})

install(TARGETS shaderc RUNTIME DESTINATION bin)
install(TARGETS noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded
    ${NOVELTEA_CLOSURE_TARGETS} ARCHIVE DESTINATION lib)
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/include/"
    DESTINATION include FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
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
