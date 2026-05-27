import sys
import os
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QLineEdit,
    QPushButton,
    QToolBar,
    QLabel,
    QStyle
)
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineCore import QWebEngineProfile


class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simsovet - Neuro Handler")
        self.resize(1200, 800)

        # Create ONE shared persistent profile for the entire application life
        self.profile = QWebEngineProfile("MyBrowserProfile", self)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        # Optional: Force it to save inside your 'data' folder
        storage_path = os.path.join(os.path.dirname(__file__), "data", "browser_profile")
        self.profile.setPersistentStoragePath(storage_path)

        # Main layout container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR (Fixed 320px width)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(320)
        self.sidebar.setStyleSheet("background-color: #2e3440; color: #d8dee9; border-right: 1px solid #4c566a;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Sidebar buttons with links
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        for label, url in [("Alice", "https://alice.yandex.ru"), ("Gemini", "https://gemini.google.com"), ("DeepSeek", "https://chat.deepseek.com")]:
            btn = QPushButton(label)
            btn.setStyleSheet("padding: 8px; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; color: #eceff4; font-weight: bold; font-size: 10px;")
            btn.clicked.connect((lambda u, l: lambda: self.add_new_tab(QUrl(u), l))(url, label))
            btn_layout.addWidget(btn)
        sidebar_layout.addWidget(btn_container)
        sidebar_layout.addStretch() # Pushes content to the top

        # 2. MAIN BROWSER AREA (Right Side)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Navigation Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        right_layout.addWidget(self.toolbar)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        right_layout.addWidget(self.tabs)

        # Assemble Main Layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_container)

        # Build the Toolbar UI
        self.create_toolbar_actions()

        # Open default initial tab
        self.add_new_tab(QUrl("https://www.google.com"), "New Tab")

    def create_toolbar_actions(self):
        """Creates and wires up all navigation buttons requested."""
        # Standard system icons used for portability
        style = QApplication.style()

        # Back Button
        self.back_btn = QPushButton()
        self.back_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.back_btn.clicked.connect(lambda: self.current_browser().back())
        self.toolbar.addWidget(self.back_btn)

        # Forward Button
        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward())
        self.toolbar.addWidget(self.forward_btn)

        # Reload Button
        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reload_btn.clicked.connect(lambda: self.current_browser().reload())
        self.toolbar.addWidget(self.reload_btn)

        # Home Button
        self.home_btn = QPushButton()
        self.home_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)) # Fallback home icon
        self.home_btn.setText("Home")
        self.home_btn.clicked.connect(self.navigate_home)
        self.toolbar.addWidget(self.home_btn)

        self.toolbar.addSeparator()

        # URL Input Bar
        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_input)

        # Go Button
        self.go_btn = QPushButton("Go")
        self.go_btn.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.go_btn)

        self.toolbar.addSeparator()

        # New Tab Button
        self.new_tab_btn = QPushButton("+ New Tab")
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl("https://www.google.com"), "New Tab"))
        self.toolbar.addWidget(self.new_tab_btn)

    # --- Tab Handling Logic ---
    def add_new_tab(self, qurl=None, title="New Tab"):
        """Adds a new tab using the shared global profile."""
        browser = QWebEngineView()
        
        # Use the shared profile initialized in __init__
        custom_page = CustomWebEnginePage(self, self.profile, browser)
        browser.setPage(custom_page)
        
        if qurl:
            browser.setUrl(qurl)

        # Add to Tab Widget
        i = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_url_bar(qurl, browser))
        browser.titleChanged.connect(lambda title, browser=browser: self.update_tab_title(title, browser))

        return browser

    def close_tab(self, index):
        """Closes the targeted tab and explicitly disposes of the web engine assets."""
        if self.tabs.count() < 2:
            return
            
        browser = self.tabs.widget(index)
        if browser:
            # Disconnect the page from the view cleanly before deleting
            browser.setPage(None) 
            browser.deleteLater()
            
        self.tabs.removeTab(index)

    def current_browser(self) -> QWebEngineView:
        """Helper to fetch the active tab's web engine."""
        return self.tabs.currentWidget()

    # --- Navigation Logic ---

    def navigate_home(self):
        if self.current_browser():
            self.current_browser().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        """Navigates to the written URL text. Automatically appends http:// if missing."""
        q = QUrl(self.url_input.text())
        if q.scheme() == "":
            q.setScheme("http")
        
        if self.current_browser():
            self.current_browser().setUrl(q)

    def tab_changed(self, index):
        """Triggers when switching tabs to synchronize the URL bar and buttons."""
        browser = self.tabs.widget(index)
        if browser:
            self.update_url_bar(browser.url(), browser)

    def update_url_bar(self, qurl, browser=None):
        """Updates the URL line edit text and back/forward buttons state."""
        # Ensure we only update if the event comes from the currently active tab
        if browser != self.current_browser():
            return
        
        self.url_input.setText(qurl.toString())
        
        # Enable or disable buttons depending on page history
        self.back_btn.setEnabled(browser.history().canGoBack())
        self.forward_btn.setEnabled(browser.history().canGoForward())

    def update_tab_title(self, title, browser=None):
        """Updates the actual tab title text dynamically."""
        index = self.tabs.indexOf(browser)
        if index != -1:
            # Crop string if title is excessively long
            short_title = title[:15] + "..." if len(title) > 15 else title
            self.tabs.setTabText(index, short_title)

    def closeEvent(self, event):
        """Forces all WebEngine pages to delete themselves before the profile is destroyed on exit."""
        # Loop through all tabs backwards and destroy them
        for i in reversed(range(self.tabs.count())):
            browser = self.tabs.widget(i)
            if browser:
                # 1. Break the link between the view and the page
                browser.setPage(None)
                # 2. Tell Qt to delete the browser object immediately
                browser.deleteLater()
        
        # Clear the tab widget completely
        self.tabs.clear()
        
        # Process any pending deletion events right now before letting the window close
        QApplication.sendPostedEvents()
        QApplication.processEvents()
        
        # Accept the close event to exit normally
        event.accept()

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, browser_window, profile, *args, **kwargs):
        # Pass the profile to the super class so the page uses it
        super().__init__(profile, *args, **kwargs)
        self.browser_window = browser_window

    def createWindow(self, _type):
        """Intercepts target='_blank' links and opens them in a new tab."""
        new_browser = self.browser_window.add_new_tab(qurl=None, title="Loading...")
        return new_browser.page()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebBrowser()
    window.show()
    sys.exit(app.exec())

