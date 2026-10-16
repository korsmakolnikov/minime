cmake_minimum_required(VERSION 3.21)
project({{PROJECT_NAME}} LANGUAGES C)

# --- Language standard (overridable: -DCMAKE_C_STANDARD=17) -------------------
set(CMAKE_C_STANDARD {{C_STANDARD}} CACHE STRING "C standard (11, 17, 23, ...)")
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- Target architecture (overridable: -DTARGET_ARCH=i686) --------------------
set(TARGET_ARCH "{{TARGET_ARCH}}" CACHE STRING "Target architecture (x86_64, i686, aarch64, ...)")
if(NOT TARGET_ARCH STREQUAL CMAKE_HOST_SYSTEM_PROCESSOR)
  if(TARGET_ARCH MATCHES "^(i[3-6]86)$" AND CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "x86_64")
    add_compile_options(-m32)
    add_link_options(-m32)
  elseif(NOT CMAKE_TOOLCHAIN_FILE AND NOT CMAKE_C_COMPILER MATCHES "${TARGET_ARCH}")
    message(WARNING
      "TARGET_ARCH=${TARGET_ARCH} differs from the host (${CMAKE_HOST_SYSTEM_PROCESSOR}). "
      "Cross-compiling requires -DCMAKE_C_COMPILER=<cross-gcc> or -DCMAKE_TOOLCHAIN_FILE=<file>.")
  endif()
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

# --- Library: everything in src/ except main.c --------------------------------
file(GLOB_RECURSE LIB_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.c)
list(FILTER LIB_SOURCES EXCLUDE REGEX "/main\\.c$")

add_library({{PROJECT_IDENT}}_lib STATIC ${LIB_SOURCES})
target_include_directories({{PROJECT_IDENT}}_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# --- Executable ---------------------------------------------------------------
add_executable({{PROJECT_NAME}} src/main.c)
target_link_libraries({{PROJECT_NAME}} PRIVATE {{PROJECT_IDENT}}_lib)

# --- Tests (Unity) ------------------------------------------------------------
option(BUILD_TESTS "Build unit tests (Unity)" ON)
if(BUILD_TESTS)
  include(FetchContent)
  FetchContent_Declare(unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG        v2.6.1
    GIT_SHALLOW    TRUE)
  FetchContent_MakeAvailable(unity)

  enable_testing()
  file(GLOB_RECURSE TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.c)
  add_executable(test_{{PROJECT_IDENT}} ${TEST_SOURCES})
  target_link_libraries(test_{{PROJECT_IDENT}} PRIVATE {{PROJECT_IDENT}}_lib unity)
  add_test(NAME test_{{PROJECT_IDENT}} COMMAND test_{{PROJECT_IDENT}})
endif()
