const electron = require("electron");
const url = require("url");
const path = require("path");
const {app, BrowserWindow, Menu} = electron;

process.env.NODE_ENV = "dev"
let mainWindow = null;

app.on("ready", () => {
    mainWindow = new BrowserWindow();
    mainWindow.loadURL(url.format({
        pathname: path.join(__dirname, "mainWindow.html"),
        protocol: "file:",
        slashes: true
    }));

    const mainMenu = Menu.buildFromTemplate(mainMenuTemplate);
    Menu.setApplicationMenu(mainMenu);
})

const mainMenuTemplate = [
    {
        label: "File",
        submenu: [
            {
                label: "Close",
                accelerator: isMac() ? "Command+Q" : "Ctrl+Q",
                click() {app.quit();}
            }
        ]
    }
];
if (isMac()) {mainMenuTemplate.unshift({});}
if (!isProduction()) {
    mainMenuTemplate.push({
        label: "DevTools",
        submenu: [
            {
                label: "Toggle",
                accelerator: isMac() ? "Command+I" : "Ctrl+I",
                click(item, focusedWindow) {focusedWindow.toggleDevTools();}
            },
            {role: "reload"}
        ]
    })
}

function isMac() {return process.platform == "darwin";}
function isProduction() {return process.env.NODE_ENV == "prod";}