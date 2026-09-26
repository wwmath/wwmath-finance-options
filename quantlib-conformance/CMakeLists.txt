cmake_minimum_required(VERSION 3.20)
project(wwmath_quantlib_conformance CXX)

# The WWMath side is C++ generated from the paper ASTs (include/wwmath/generated); the
# reference side is the QuantLib C++ library. Point CMAKE_PREFIX_PATH at a QuantLib install,
# or set WWMATH_FETCH_QUANTLIB=ON to build QuantLib from the commit the research cites.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

option(WWMATH_FETCH_QUANTLIB "Fetch and build QuantLib at the pinned commit" OFF)
set(WWMATH_QUANTLIB_COMMIT 0191ca7cccbb62e538fd10f5c88f640594d4eaed)

include(FetchContent)
find_package(QuantLib CONFIG QUIET)
if(NOT QuantLib_FOUND)
  if(WWMATH_FETCH_QUANTLIB)
    set(QL_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
    set(QL_BUILD_TEST_SUITE OFF CACHE BOOL "" FORCE)
    set(QL_BUILD_BENCHMARK OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(QuantLib GIT_REPOSITORY https://github.com/lballabio/QuantLib.git
                                  GIT_TAG ${WWMATH_QUANTLIB_COMMIT})
    FetchContent_MakeAvailable(QuantLib)
    add_library(QuantLib::QuantLib ALIAS ql_library)
  else()
    message(FATAL_ERROR "QuantLib not found: set CMAKE_PREFIX_PATH to its install prefix, "
                        "or configure with -DWWMATH_FETCH_QUANTLIB=ON")
  endif()
endif()

find_package(GTest CONFIG QUIET)
if(NOT GTest_FOUND)
  FetchContent_Declare(googletest URL
    https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz)
  FetchContent_MakeAvailable(googletest)
endif()

# Generated WWMath formulas: header-only, standard library only.
add_library(wwmath_formulas INTERFACE)
target_include_directories(wwmath_formulas INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

enable_testing()
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS tests/test_*.cpp)
add_executable(conformance_tests ${TEST_SOURCES})
target_link_libraries(conformance_tests PRIVATE wwmath_formulas QuantLib::QuantLib
                      GTest::gtest_main)
target_compile_options(conformance_tests PRIVATE -Wall -Wextra)
include(GoogleTest)
gtest_discover_tests(conformance_tests)

add_executable(export_fixtures tools/export_fixtures.cpp)
target_link_libraries(export_fixtures PRIVATE wwmath_formulas QuantLib::QuantLib GTest::gtest)
