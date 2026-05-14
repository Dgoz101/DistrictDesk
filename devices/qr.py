"""SVG QR codes for device label printing (uses segno)."""
from django.conf import settings


def report_url_for_device(request, device) -> str:
    from django.urls import reverse

    path = reverse('devices:public_report', kwargs={'report_uuid': device.public_report_uuid})
    base = getattr(settings, 'PUBLIC_BASE_URL', '') or ''
    base = str(base).strip().rstrip('/')
    if base:
        return f'{base}{path}'
    return request.build_absolute_uri(path)


def qr_svg_data_uri(url: str) -> str:
    import segno

    qr = segno.make(url, error='m')
    return qr.svg_data_uri(scale=3, border=1, xmldecl=False, encode_minimal=True)
