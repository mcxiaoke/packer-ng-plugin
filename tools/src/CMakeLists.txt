cmake_minimum_required (VERSION 2.6)
project(packer)

set(VER_MAJOR 2)
set(VER_MINOR 0)
set(VER_PATCH 0)

include (CheckFunctionExists)

configure_file (
    "${PROJECT_SOURCE_DIR}/Config.h.in"
    "${PROJECT_BINARY_DIR}/Config.h"
    )

include_directories("${PROJECT_BINARY_DIR}")

aux_source_directory(. SOURCE)
# add_subdirectory(math)
add_executable(packer ${SOURCE})
# target_link_libraries(packer mathlib)

# in sub dir CMakeLists.txt
# aux_source_directory(. DIR_LIB_SRCS)
# add_library (mathlib ${DIR_LIB_SRCS})

install (TARGETS packer DESTINATION bin)
# install (FILES "${PROJECT_BINARY_DIR}/Config.h" DESTINATION include)