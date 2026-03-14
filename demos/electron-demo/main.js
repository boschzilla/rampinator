const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");

let mainWindow;

app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 680,
    minWidth: 720,
    minHeight: 480,
    backgroundColor: "#0d0d1a",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.loadFile("index.html");

  // Remove default menu bar for clean look
  mainWindow.setMenuBarVisibility(false);
});

// Simulated search data sent to renderer
ipcMain.handle("get-searches", () => {
  return [
    { id: "s1", name: "Mageblood", league: "Settlers", status: "Live", hits: 42 },
    { id: "s2", name: "Mirror of Kalandra", league: "Standard", status: "Live", hits: 7 },
    { id: "s3", name: "Headhunter", league: "Settlers", status: "Connecting...", hits: 0 },
    { id: "s4", name: "Divination Cards", league: "Settlers", status: "Error", hits: 18 },
  ];
});

app.on("window-all-closed", () => app.quit());
