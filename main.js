Deno.serve({
    port: 80,
    async handler(request) {
        if (request.headers.get("upgrade") !== "websocket") {
            // If the request is a normal HTTP request,
            // we serve the client HTML file.
            const file = await Deno.open("./index.html", { read: true });
            return new Response(file.readable);
        }
        // If the request is a websocket upgrade,
        // we need to use the Deno.upgradeWebSocket helper
        const { socket, response } = Deno.upgradeWebSocket(request);

        socket.onopen = () => {
            console.log("CONNECTED");
        };
        socket.onmessage = (event) => {
            console.log(`RECEIVED: ${event.data}`);
            socket.send("pong");
        };
        socket.onclose = () => console.log("DISCONNECTED");
        socket.onerror = (error) => console.error("ERROR:", error);

        return response;
    },
});

const wsUri = "ws://127.0.0.1/";
const output = document.querySelector("#output");
const websocket = new WebSocket(wsUri);
let pingInterval;

function writeToScreen(message) {
    output.insertAdjacentHTML("afterbegin", `<p>${message}</p>`);
}

function sendMessage(message) {
    writeToScreen(`SENT: ${message}`);
    websocket.send(message);
}

websocket.onopen = (e) => {
    writeToScreen("CONNECTED");
    sendMessage("ping");
    pingInterval = setInterval(() => {
        sendMessage("ping");
    }, 5000);
};

websocket.onclose = (e) => {
    writeToScreen("DISCONNECTED");
    clearInterval(pingInterval);
};

websocket.onmessage = (e) => {
    writeToScreen(`RECEIVED: ${e.data}`);
};

websocket.onerror = (e) => {
    writeToScreen(`ERROR: ${e.data}`);
};