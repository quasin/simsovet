import sys
import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
from PySide6.QtCore import QUrl, QEvent
from PySide6.QtGui import QIcon
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
    QStyle,
    QStatusBar
)
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage


class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simsovet - Neuro Handler")
        self.resize(1200, 800)

        self.base_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)

        self.db_path = os.path.join(self.data_dir, "simsovet.db")
        self.init_db()

        icon_path = os.path.join(self.base_dir, "favicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.profile = QWebEngineProfile("MyBrowserProfile", self)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        storage_path = os.path.join(self.data_dir, "browser_profile")
        self.profile.setPersistentStoragePath(storage_path)

        self.setStatusBar(QStatusBar(self))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(320)
        self.sidebar.setStyleSheet("background-color: #2e3440; color: #d8dee9; border-right: 1px solid #4c566a;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
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

        self.recent_history_section = QWidget()
        recent_history_layout = QVBoxLayout(self.recent_history_section)
        recent_history_layout.setContentsMargins(0, 0, 0, 0)
        recent_history_layout.setSpacing(5)

        history_label = QLabel("Recent History")
        history_label.setStyleSheet("color: #eceff4; font-weight: bold; font-size: 11px; padding: 10px 10px 4px 10px;")
        recent_history_layout.addWidget(history_label)

        self.recent_history_layout = recent_history_layout

        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.recent_history_section)

        self.db_status_label = QLabel()
        self.db_status_label.setStyleSheet("color: #81a1c1; font-size: 11px; padding: 10px; border-top: 1px solid #4c566a;")
        self.db_status_label.setWordWrap(True)
        sidebar_layout.addWidget(self.db_status_label)
        self.update_sidebar_status()

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        right_layout.addWidget(self.toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tab_titles = {}
        self.tabs.tabBar().setMouseTracking(True)
        self.tabs.tabBar().installEventFilter(self)
        right_layout.addWidget(self.tabs)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_container)

        self.create_toolbar_actions()

        self.add_new_tab(QUrl("https://www.google.com"), "New Tab")

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT NOT NULL,
                visited_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def log_to_history(self, title, url):
        if not url or url == "about:blank":
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO history (title, url, visited_at) VALUES (?, ?, ?)",
                (title, url, now)
            )
            conn.commit()
            conn.close()
            self.update_sidebar_status()
        except sqlite3.Error as e:
            print(f"Ошибка логирования в БД: {e}")

    def refresh_recent_history(self):
        while self.recent_history_layout.count():
            item = self.recent_history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        history_label = QLabel("Recent History")
        history_label.setStyleSheet("color: #eceff4; font-weight: bold; font-size: 11px; padding: 10px 10px 4px 10px;")
        self.recent_history_layout.addWidget(history_label)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT title, url FROM history ORDER BY id DESC LIMIT 3")
            recent_rows = cursor.fetchall()
            conn.close()
        except sqlite3.Error:
            recent_rows = []

        for title, url in recent_rows:
            if not url:
                continue

            display_text = url
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."

            btn = QPushButton(display_text)
            btn.setToolTip(url)
            btn.setStyleSheet("padding: 8px; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 4px; color: #eceff4; font-size: 10px; text-align: left;")
            btn.clicked.connect(lambda checked=False, u=url, display_title=title: self.add_new_tab(QUrl(u), display_title or u))
            self.recent_history_layout.addWidget(btn)

        if not recent_rows:
            empty_label = QLabel("No history yet")
            empty_label.setStyleSheet("color: #d8dee9; font-size: 10px; padding: 0 10px 10px 10px;")
            self.recent_history_layout.addWidget(empty_label)

    def update_sidebar_status(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM history")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT url FROM history")
            urls = cursor.fetchall()
            domains = {urlparse(row[0]).netloc for row in urls if row[0]}
            unique_domains = len(domains)
            
            cursor.execute("SELECT visited_at FROM history ORDER BY id DESC LIMIT 1")
            last_time_row = cursor.fetchone()
            last_time = last_time_row[0].split(" ")[1] if last_time_row else "None"
            
            conn.close()
            
            status_text = f"Total: {total_count} | Domains: {unique_domains} | Last: {last_time}"
            self.db_status_label.setText(status_text)
            self.refresh_recent_history()
        except sqlite3.Error:
            self.db_status_label.setText("DB: Error loading statistics")

    def create_toolbar_actions(self):
        style = QApplication.style()

        self.back_btn = QPushButton()
        self.back_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.back_btn.clicked.connect(lambda: self.current_browser().back())
        self.toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward())
        self.toolbar.addWidget(self.forward_btn)

        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reload_btn.clicked.connect(lambda: self.current_browser().reload())
        self.toolbar.addWidget(self.reload_btn)

        self.home_btn = QPushButton()
        self.home_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)) 
        self.home_btn.setText("Home")
        self.home_btn.clicked.connect(self.navigate_home)
        self.toolbar.addWidget(self.home_btn)

        self.toolbar.addSeparator()

        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_input)

        self.go_btn = QPushButton("Go")
        self.go_btn.clicked.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.go_btn)

        self.toolbar.addSeparator()

        self.new_tab_btn = QPushButton("+ New Tab")
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl("https://www.google.com"), "New Tab"))
        self.toolbar.addWidget(self.new_tab_btn)

    def add_new_tab(self, qurl=None, title="New Tab"):
        browser = QWebEngineView()
        
        custom_page = CustomWebEnginePage(self, self.profile, browser)
        custom_page.linkHovered.connect(self.show_link_in_status_bar)
        browser.setPage(custom_page)
        
        if qurl:
            browser.setUrl(qurl)

        i = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(i)
        self.tab_titles[browser] = title

        # Handles address bar visual updates
        browser.urlChanged.connect(lambda qurl, b=browser: self.update_url_bar(qurl, b))
        
        # Dedicated handler to intercept background tabs / targets asynchronously
        browser.urlChanged.connect(lambda qurl, b=browser: self.handle_history_logging(qurl, b))
        
        browser.titleChanged.connect(lambda t, b=browser: self.update_tab_title(t, b))

        return browser

    def close_tab(self, index):
        if self.tabs.count() < 2:
            return
            
        browser = self.tabs.widget(index)
        if browser:
            self.tab_titles.pop(browser, None)
            browser.setPage(None) 
            browser.deleteLater()
            
        self.tabs.removeTab(index)

    def current_browser(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def navigate_home(self):
        if self.current_browser():
            self.current_browser().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        q = QUrl(self.url_input.text())
        if q.scheme() == "":
            q.setScheme("http")
        
        if self.current_browser():
            self.current_browser().setUrl(q)

    def tab_changed(self, index):
        browser = self.tabs.widget(index)
        if browser:
            self.update_url_bar(browser.url(), browser)

    def update_url_bar(self, qurl, browser=None):
        if browser != self.current_browser():
            return
        
        url_str = qurl.toString()
        self.url_input.setText(url_str)
        self.back_btn.setEnabled(browser.history().canGoBack())
        self.forward_btn.setEnabled(browser.history().canGoForward())

    def handle_history_logging(self, qurl, browser):
        url_str = qurl.toString()
        if not url_str or url_str == "about:blank":
            return

        # Fetch structural/dynamic titles safely, default to domain if unavailable yet
        title = self.tab_titles.get(browser, "Loading...")
        if title in ["Loading...", "New Tab"] and browser.title():
            title = browser.title()
        elif title in ["Loading...", "New Tab"]:
            title = urlparse(url_str).netloc

        self.log_to_history(title, url_str)

    def update_tab_title(self, title, browser=None):
        index = self.tabs.indexOf(browser)
        if index != -1:
            self.tab_titles[browser] = title
            self.tabs.setTabToolTip(index, title)
            short_title = title[:15] + "..." if len(title) > 15 else title
            self.tabs.setTabText(index, short_title)

    def eventFilter(self, watched, event):
        if watched == self.tabs.tabBar():
            if event.type() == QEvent.Type.MouseMove:
                tab_index = self.tabs.tabBar().tabAt(event.position().toPoint())
                if tab_index != -1:
                    browser = self.tabs.widget(tab_index)
                    full_title = self.tab_titles.get(browser)
                    if full_title:
                        self.statusBar().showMessage(full_title)
                    else:
                        self.statusBar().clearMessage()
                else:
                    self.statusBar().clearMessage()
            elif event.type() == QEvent.Type.Leave:
                self.statusBar().clearMessage()

        return super().eventFilter(watched, event)

    def show_link_in_status_bar(self, link):
        if link:
            self.statusBar().showMessage(str(link))
        else:
            self.statusBar().clearMessage()

    def closeEvent(self, event):
        for i in reversed(range(self.tabs.count())):
            browser = self.tabs.widget(i)
            if browser:
                browser.setPage(None)
                browser.deleteLater()
        
        self.tabs.clear()
        QApplication.sendPostedEvents()
        QApplication.processEvents()
        event.accept()


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, browser_window, profile, *args, **kwargs):
        super().__init__(profile, *args, **kwargs)
        self.browser_window = browser_window

    def createWindow(self, _type):
        new_browser = self.browser_window.add_new_tab(qurl=None, title="Loading...")
        return new_browser.page()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if sys.platform == "win32":
        import ctypes
        myappid = "simsovet.neurohandler.browser.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    window = WebBrowser()
    window.show()
    sys.exit(app.exec())