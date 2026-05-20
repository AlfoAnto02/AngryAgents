from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    keep_trailing_newline=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_name: str, **kwargs) -> tuple[str, str]:
    tmpl = _env.get_template(template_name)
    ctx = tmpl.new_context(vars=kwargs)
    system, user = "", ""
    for name, block_fn in tmpl.blocks.items():
        rendered = "".join(block_fn(ctx)).strip()
        if name == "system":
            system = rendered
        elif name == "user":
            user = rendered
    if not system or not user:
        raise ValueError(
            f"{template_name} must define both {{% block system %}} and {{% block user %}}"
        )
    return system, user
