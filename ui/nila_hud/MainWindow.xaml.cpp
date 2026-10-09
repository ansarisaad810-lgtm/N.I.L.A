#include "pch.h"
#include "MainWindow.xaml.h"
#if __has_include("MainWindow.g.cpp")
#include "MainWindow.g.cpp"
#endif

#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Windowing.h>
#include <winrt/Microsoft.UI.Interop.h>
#include <winrt/Windows.UI.Core.h>
#include "ws_client/nila_ipc_client.hpp"

using namespace winrt;
using namespace Microsoft::UI::Xaml;

namespace winrt::NILAHUD::implementation
{
    static NILA::IPC::NILAIPCClient g_ipcClient;

    MainWindow::MainWindow()
    {
        InitializeComponent();

        // 1. Make window borderless & always-on-top HUD
        auto hwnd = winrt::Microsoft::UI::GetWindowFromWindowId(this->AppWindow().Id());
        SetWindowLong((HWND)hwnd, GWL_STYLE, WS_POPUP | WS_VISIBLE);
        SetWindowPos((HWND)hwnd, HWND_TOPMOST, 100, 100, 450, 280, SWP_SHOWWINDOW);

        // 2. Attach WebSocket IPC Callbacks
        g_ipcClient.SetOnMessage([this](const std::string& msg) {
            this->DispatcherQueue().TryEnqueue([this, msg]() {
                // Update response block with token/message string
                std::wstring wideMsg(msg.begin(), msg.end());
                ResponseTextBlock().Text(wideMsg);
            });
        });

        // 3. Connect to Python Brain WS
        g_ipcClient.ConnectAsync(L"ws://127.0.0.1:8765");
    }

    void MainWindow::OnSendClick(IInspectable const&, RoutedEventArgs const&)
    {
        SendCommand();
    }

    void MainWindow::OnCommandKeyDown(IInspectable const&, Input::KeyRoutedEventArgs const& e)
    {
        if (e.Key() == Windows::System::VirtualKey::Enter)
        {
            SendCommand();
        }
    }

    void MainWindow::SendCommand()
    {
        hstring input = CommandBox().Text();
        if (input.empty()) return;

        std::string payload = "{\"type\":\"user_intent\",\"payload\":{\"text\":\"" + to_string(input) + "\"}}";
        g_ipcClient.SendIntentAsync(payload);

        StatusText().Text(L"N.I.L.A. THINKING...");
        CommandBox().Text(L"");
    }
}
