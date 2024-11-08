def get_brand_logo_static_path(request):
    from ephios.core.signals import brand_logo_static_path

    for _, result in brand_logo_static_path.send(None, request=request):
        if result:
            return result
    return "ephios/img/ephios-text-black.png"
