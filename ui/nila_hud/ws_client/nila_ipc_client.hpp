#pragma once

#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Networking.Sockets.h>
#include <winrt/Windows.Storage.Streams.h>
#include <functional>
#include <string>

namespace NILA::IPC {

class NILAIPCClient {
public:
    using MessageHandler = std::function<void(const std::string&)>;

    NILAIPCClient() = default;

    async winrt::Windows::Foundation::IAsyncAction ConnectAsync(const std::wstring& uriStr) {
        try {
            winrt::Windows::Foundation::Uri uri(uriStr);
            m_socket = winrt::Windows::Networking::Sockets::MessageWebSocket();
            m_socket.Control().MessageType(winrt::Windows::Networking::Sockets::SocketMessageType::Utf8);

            m_messageToken = m_socket.MessageReceived({ this, &NILAIPCClient::OnMessageReceived });

            co_await m_socket.ConnectAsync(uri);
            m_writer = winrt::Windows::Storage::Streams::DataWriter(m_socket.OutputStream());
            m_isConnected = true;
        } catch (...) {
            m_isConnected = false;
        }
    }

    void SetOnMessage(MessageHandler handler) {
        m_onMessage = handler;
    }

    async winrt::Windows::Foundation::IAsyncAction SendIntentAsync(const std::string& intentJson) {
        if (!m_isConnected || !m_writer) co_return;

        m_writer.WriteString(winrt::single_threaded_vector<winrt::hstring>({ winrt::to_hstring(intentJson) }).GetAt(0));
        co_await m_writer.StoreAsync();
    }

private:
    void OnMessageReceived(
        winrt::Windows::Networking::Sockets::MessageWebSocket const&,
        winrt::Windows::Networking::Sockets::MessageWebSocketMessageReceivedEventArgs const& args) 
    {
        try {
            auto reader = args.GetDataReader();
            std::string message = winrt::to_string(reader.ReadString(reader.UnconsumedBufferLength()));
            if (m_onMessage) {
                m_onMessage(message);
            }
        } catch (...) {}
    }

    winrt::Windows::Networking::Sockets::MessageWebSocket m_socket{ nullptr };
    winrt::Windows::Storage::Streams::DataWriter m_writer{ nullptr };
    winrt::event_token m_messageToken;
    MessageHandler m_onMessage;
    bool m_isConnected{ false };
};

} // namespace NILA::IPC
