cmake_minimum_required(VERSION 3.24)
project(noveltea_shaderc_toolchain LANGUAGES C CXX)

include(FetchContent)

set(NOVELTEA_SHADERC_BGFX_ARCHIVE_URL
    "https://github.com/bkaradzic/bgfx.cmake/releases/download/v1.129.8940-496/bgfx.cmake.v1.129.8940-496.tar.gz")
set(NOVELTEA_SHADERC_BGFX_ARCHIVE_SHA256
    "0fa0482d3b09ae262c9c7fc54a7193022510313f1250077caad5ff18504fce02")

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

get_target_property(NOVELTEA_SHADERC_SOURCES shaderc SOURCES)
get_target_property(NOVELTEA_SHADERC_LINKS shaderc LINK_LIBRARIES)
if(NOT NOVELTEA_SHADERC_SOURCES OR NOT NOVELTEA_SHADERC_LINKS)
    message(FATAL_ERROR "Pinned bgfx shaderc target did not expose its source/link closure")
endif()

add_library(noveltea_bgfx_shaderc_embedded STATIC ${NOVELTEA_SHADERC_SOURCES})
set_target_properties(noveltea_bgfx_shaderc_embedded PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_compile_definitions(noveltea_bgfx_shaderc_embedded PRIVATE
    main=noveltea_bgfx_shaderc_embedded_cli_main)
target_link_libraries(noveltea_bgfx_shaderc_embedded PUBLIC ${NOVELTEA_SHADERC_LINKS})
target_include_directories(noveltea_bgfx_shaderc_embedded PUBLIC
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/tools/shaderc>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src>"
    "$<BUILD_INTERFACE:${noveltea_shaderc_bgfx_SOURCE_DIR}/bx/include>")

get_target_property(NOVELTEA_TEXTUREC_SOURCES texturec SOURCES)
get_target_property(NOVELTEA_TEXTUREC_LINKS texturec LINK_LIBRARIES)
if(NOT NOVELTEA_TEXTUREC_SOURCES OR NOT NOVELTEA_TEXTUREC_LINKS)
    message(FATAL_ERROR "Pinned bgfx texturec target did not expose its source/link closure")
endif()

add_library(noveltea_bimg_texturec_embedded STATIC ${NOVELTEA_TEXTUREC_SOURCES})
set_target_properties(noveltea_bimg_texturec_embedded PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_compile_definitions(noveltea_bimg_texturec_embedded PRIVATE
    main=noveltea_bimg_texturec_main)
target_link_libraries(noveltea_bimg_texturec_embedded PUBLIC ${NOVELTEA_TEXTUREC_LINKS})

foreach(noveltea_shaderc_dependency IN ITEMS bx bimg fcpp glslang glsl-optimizer spirv-opt spirv-cross)
    if(NOT TARGET ${noveltea_shaderc_dependency})
        message(FATAL_ERROR "Pinned bgfx shaderc closure is missing ${noveltea_shaderc_dependency}")
    endif()
endforeach()

foreach(noveltea_texturec_dependency IN ITEMS bx bimg bimg_decode bimg_encode)
    if(NOT TARGET ${noveltea_texturec_dependency})
        message(FATAL_ERROR "Pinned bgfx texturec closure is missing ${noveltea_texturec_dependency}")
    endif()
endforeach()

add_custom_target(noveltea_shaderc_bundle ALL DEPENDS
    noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded
    bx bimg bimg_decode bimg_encode fcpp glslang glsl-optimizer spirv-opt spirv-cross)

install(TARGETS
    noveltea_bgfx_shaderc_embedded noveltea_bimg_texturec_embedded
    bx bimg bimg_decode bimg_encode fcpp glslang glsl-optimizer spirv-opt spirv-cross
    ARCHIVE DESTINATION lib)
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/tools/shaderc/"
    DESTINATION include/bgfx/tools/shaderc FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/"
    DESTINATION include/bgfx/src FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(DIRECTORY "${noveltea_shaderc_bgfx_SOURCE_DIR}/bx/include/"
    DESTINATION include/bx FILES_MATCHING
    PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.inl")
install(FILES
    "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/bgfx_shader.sh"
    "${noveltea_shaderc_bgfx_SOURCE_DIR}/bgfx/src/bgfx_compute.sh"
    DESTINATION resources)
configure_file(cmake/noveltea_shaderc_toolchain.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/noveltea_shaderc_toolchain.cmake" @ONLY)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/noveltea_shaderc_toolchain.cmake" DESTINATION cmake)
