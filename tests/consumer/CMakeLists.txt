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
