from django.forms import CheckboxInput, FileInput, Select, SelectMultiple, Textarea, Widget


def apply_bootstrap(form) -> None:
    for field in form.fields.values():
        widget: Widget = field.widget
        existing = widget.attrs.get("class", "")
        if isinstance(widget, CheckboxInput):
            widget.attrs["class"] = f"{existing} form-check-input".strip()
        elif isinstance(widget, SelectMultiple):
            widget.attrs["class"] = f"{existing} form-select".strip()
            widget.attrs["size"] = widget.attrs.get("size", "6")
        elif isinstance(widget, Select):
            widget.attrs["class"] = f"{existing} form-select".strip()
        elif isinstance(widget, Textarea):
            widget.attrs["class"] = f"{existing} form-control".strip()
            widget.attrs.setdefault("rows", 3)
        elif isinstance(widget, FileInput):
            widget.attrs["class"] = f"{existing} form-control".strip()
        else:
            widget.attrs["class"] = f"{existing} form-control".strip()
