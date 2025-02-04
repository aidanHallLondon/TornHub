import os
from string import Template


def move_template_file_with_subs(
    template_file_path, out_path, out_filename, substitutions=None
):
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    #
    final_html = html_template.safe_substitute(substitutions)
    #
    out_filepath = os.path.join(out_path, out_filename)
    if out_path>"" and not os.path.exists(out_path):
        os.makedirs(out_path)
    print("out_filepath",out_filepath)
    with open(out_filepath, "w") as f:
        f.write(final_html)

