from .qtimports import *
import ctypes


class Browser(QWidget):
    """Web browser widget used for authentication."""

    windowCloseRequested = Signal()
    loadFinished = Signal()

    def __init__(self, title=None):
        super().__init__()
        self.__scale = self.__get_scale() or 1.0
        self.__init_ui(title)

    def __init_ui(self, title=None):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        size = QSize(400 * self.__scale, 600 * self.__scale)

        rect = QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            size,
            QApplication.instance().desktop().availableGeometry())

        self.setGeometry(rect)

        if title:
            self.setWindowTitle(title)

        # Create the Qt browser
        self.browser = QWebEngineView()
        self.profile = QWebEngineProfile()
        self.page = QWebEnginePage(self.profile, self.browser)

        # Connect the signals
        self.page.windowCloseRequested.connect(self.windowCloseRequested)
        self.page.loadFinished.connect(self.loadFinished)

        # Add the browser to the layout and show the window
        layout.addWidget(self.browser)
        self.show()

    def closeEvent(self, event):
        self.windowCloseRequested.emit()

    def setUrl(self, url):
        # Navigate to the URL and show the browser
        self.page.setUrl(QUrl(url))
        self.browser.setPage(self.page)
        self.browser.setZoomFactor(self.__scale)
        self.browser.show()

    def runJavaScript(self, scriptSource, resultCallback):
        self.page.runJavaScript(scriptSource, QWebEngineScript.ApplicationWorld, resultCallback)

    def cookieStore(self):
        return self.profile.cookieStore()

    def __get_scale(self):
        """Return the scale to use for the browser window based on the window DPI."""
        LOGPIXELSX = 88
        hwnd = self.winId()
        if isinstance(hwnd, str):
            hwnd = int(hwnd, 16 if hwnd.startswith("0x") else 10)
        hwnd = ctypes.c_size_t(hwnd)
        screen = ctypes.windll.user32.GetDC(hwnd)
        try:
            return ctypes.windll.gdi32.GetDeviceCaps(screen, LOGPIXELSX) / 96.0
        finally:
            ctypes.windll.user32.ReleaseDC(hwnd, screen)
