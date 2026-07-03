from browser_manager import BrowserManager
from console_menu import ConsoleMenu


def main():
    print("\n==============================")
    print(" CONFIGURATION... ")
    print("==============================\n")

    browser_manager = BrowserManager()
    driver = browser_manager.setup()

    browser_manager.open_auth_page()
    browser_manager.wait_for_auth()

    menu = ConsoleMenu(driver, browser_manager)
    menu.run()


if __name__ == "__main__":
    main()