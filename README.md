# nt-tools

Publishes the pinned Linux x64 static-library closure used by NovelTea's embedded bgfx shader and
texture compilers. Push a tag to create a GitHub release containing
`noveltea-bgfx-shaderc-linux-x64.tar.gz` and its SHA-256 checksum.

The archive contains the `noveltea_bgfx_shaderc_embedded` and
`noveltea_bimg_texturec_embedded` archives, every required bgfx/bx/bimg static dependency, headers,
shader include resources, and a CMake import file. Consumers include
`cmake/noveltea_shaderc_toolchain.cmake` from an extracted archive and link the independent
`noveltea_shaderc::embedded` and `noveltea_texturec::embedded` targets they use.
