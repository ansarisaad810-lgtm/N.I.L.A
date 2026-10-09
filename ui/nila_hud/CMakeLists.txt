cmake_minimum_required(VERSION 3.20)
project(NILAHUD LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_definitions(-DWINUIRUNTIME_STATIC_LIB)

find_package(cppwinrt CONFIG REQUIRED)

add_executable(NILAHUD
    MainWindow.xaml.cpp
    ws_client/nila_ipc_client.hpp
)

target_include_directories(NILAHUD PRIVATE \)

target_link_libraries(NILAHUD PRIVATE
    Microsoft::CppWinRT
    onecore
)