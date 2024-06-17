from fireconfig import AppPackage


def test_app_package_id():
    class TestAppPackage(AppPackage):
        def compile(self, app):
            pass

    class HTTPTestAppPackage(AppPackage):
        def compile(self, app):
            pass

    assert TestAppPackage.id() == "test-app-package"
    tap = TestAppPackage()
    assert tap.id() == "test-app-package"
    assert HTTPTestAppPackage.id() == "h-t-t-p-test-app-package"
