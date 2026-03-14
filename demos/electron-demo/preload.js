const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  getSearches: () => ipcRenderer.invoke("get-searches"),
});
