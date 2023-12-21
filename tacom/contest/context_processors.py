from django.conf import settings


def test_env(request):
    return {'TEST_ENV': settings.TEST_ENV}
