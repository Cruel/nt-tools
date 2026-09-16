cmake_minimum_required(VERSION 3.24)
project(noveltea_toolchain_consumer LANGUAGES CXX)

if(NOT NOVELTEA_TOOLCHAIN_FILE)
    message(FATAL_ERROR "NOVELTEA_TOOLCHAIN_FILE is required")
endif()

include("${NOVELTEA_TOOLCHAIN_FILE}")

add_library(noveltea_toolchain_smoke MODULE embedded_tools.cpp)
target_link_libraries(noveltea_toolchain_smoke PRIVATE
    noveltea_shaderc::embedded
    noveltea_texturec::embedded)

add_executable(noveltea_shaderc_smoke shaderc_smoke.cpp)
set_target_properties(noveltea_shaderc_smoke PROPERTIES
    CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
target_link_libraries(noveltea_shaderc_smoke PRIVATE noveltea_shaderc::embedded)

include(CTest)
if(BUILD_TESTING)
    set(_noveltea_shader "${CMAKE_CURRENT_BINARY_DIR}/smoke.sc")
    set(_noveltea_varying "${CMAKE_CURRENT_BINARY_DIR}/varying.def.sc")
    file(WRITE "${_noveltea_shader}" "\$input a_position\nvoid main() { gl_Position = a_position; }\n")
    file(WRITE "${_noveltea_varying}" "vec4 a_position : POSITION;\n")
    add_test(NAME shaderc_glsl330 COMMAND noveltea_shaderc_smoke
        -f "${_noveltea_shader}" -o "${CMAKE_CURRENT_BINARY_DIR}/glsl330.bin"
        --varyingdef "${_noveltea_varying}" --type v --platform linux --profile 330 -i "${NOVELTEA_SHADERC_TOOLCHAIN_RESOURCE_DIR}")
    add_test(NAME shaderc_essl300 COMMAND noveltea_shaderc_smoke
        -f "${_noveltea_shader}" -o "${CMAKE_CURRENT_BINARY_DIR}/essl300.bin"
        --varyingdef "${_noveltea_varying}" --type v --platform android --profile 300_es -i "${NOVELTEA_SHADERC_TOOLCHAIN_RESOURCE_DIR}")
    add_test(NAME shaderc_metal COMMAND noveltea_shaderc_smoke
        -f "${_noveltea_shader}" -o "${CMAKE_CURRENT_BINARY_DIR}/metal.bin"
        --varyingdef "${_noveltea_varying}" --type v --platform osx --profile metal -i "${NOVELTEA_SHADERC_TOOLCHAIN_RESOURCE_DIR}")
endif()
