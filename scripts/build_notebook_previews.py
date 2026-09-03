"""Build website preview images from the saved outputs in the Utilities notebooks.

The script never recomputes a model. It extracts the final saved output from each
notebook and writes the compact two-panel summary highlighted on the website.
Run this after executing the notebooks.

Usage:
    py -3 scripts/build_notebook_previews.py PATH_TO_UTILITIES
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def saved_png(notebook: Path, image_number: int = -1) -> Image.Image:
    """Return one embedded PNG output from a notebook as an RGB image."""
    data = json.loads(notebook.read_text(encoding="utf-8"))
    outputs: list[str] = []
    for cell in data.get("cells", []):
        for output in cell.get("outputs", []):
            png = output.get("data", {}).get("image/png")
            if png:
                outputs.append("".join(png) if isinstance(png, list) else png)
    if not outputs:
        raise ValueError(f"No saved PNG output found in {notebook}")
    return Image.open(io.BytesIO(base64.b64decode(outputs[image_number]))).convert("RGB")


def saved_svg(notebook: Path) -> str:
    """Return the first embedded SVG output from a notebook."""
    data = json.loads(notebook.read_text(encoding="utf-8"))
    for cell in data.get("cells", []):
        for output in cell.get("outputs", []):
            svg = output.get("data", {}).get("image/svg+xml")
            if svg:
                return "".join(svg) if isinstance(svg, list) else svg
    raise ValueError(f"No saved SVG output found in {notebook}")


def polyline_points(element: ET.Element) -> np.ndarray:
    """Parse an SVG polyline's coordinate pairs."""
    return np.array(
        [tuple(map(float, pair.split(","))) for pair in element.attrib["points"].split()],
        dtype=float,
    )


def flux_preview(notebook: Path) -> Image.Image:
    """Rebuild the Flux summary from the notebook's exact saved SVG curves.

    The original Julia diagnostic is a three-panel, near-square image. Replotting
    its training and policy polylines gives the website the same wide two-panel
    composition as the other method previews without stretching the source image.
    """
    root = ET.fromstring(saved_svg(notebook))
    blue_lines: dict[str, list[ET.Element]] = {"url(#clip302)": [], "url(#clip303)": []}
    for element in root.iter():
        if not element.tag.endswith("polyline"):
            continue
        clip = element.attrib.get("clip-path")
        style = element.attrib.get("style", "")
        if clip in blue_lines and "stroke:#009af9" in style:
            blue_lines[clip].append(element)

    if not all(blue_lines.values()):
        raise ValueError(f"Could not locate the Flux training and policy curves in {notebook}")

    training_svg = polyline_points(
        max(blue_lines["url(#clip302)"], key=lambda element: len(element.attrib["points"]))
    )
    policy_svg = polyline_points(
        max(blue_lines["url(#clip303)"], key=lambda element: len(element.attrib["points"]))
    )

    # Axis coordinates recovered from the tick-grid positions in the saved SVG.
    training_loss = -2.0 + (training_svg[:, 1] - 637.557) * (
        (-4.0 + 2.0) / (1594.62 - 637.557)
    )
    policy = 0.8 + (policy_svg[:, 1] - 420.659) * (
        (0.2 - 0.8) / (1911.87 - 420.659)
    )
    loans = np.linspace(0.1, 0.9, policy.size)

    fig, (loss_axis, policy_axis) = plt.subplots(
        1, 2, figsize=(11.5, 5), constrained_layout=True
    )
    loss_axis.plot(training_loss, color="#4c78a8", linewidth=0.55)
    loss_axis.set(
        title="Training Loss",
        xlabel="Epoch",
        ylabel="Loss (log10 scale)",
    )
    loss_axis.grid(alpha=0.18)

    policy_axis.plot(
        loans,
        policy,
        color="#4c78a8",
        linewidth=1.7,
        label="Learned Policy l'(l)",
    )
    policy_axis.plot(
        [0.1, 0.9],
        [0.1, 0.9],
        color="black",
        linestyle="--",
        linewidth=1.3,
        label="45-degree line",
    )
    policy_axis.set(
        title="Policy Function (at lowest shocks)",
        xlabel="Current Loans (l)",
        ylabel="Next Period's Loans (l')",
    )
    policy_axis.grid(alpha=0.18)
    policy_axis.legend(frameon=True)

    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=150, facecolor="white")
    plt.close(fig)
    output.seek(0)
    return Image.open(output).convert("RGB")


def save(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if image.width > 1600:
        height = round(image.height * 1600 / image.width)
        image = image.resize((1600, height), Image.Resampling.LANCZOS)
    image.save(destination, format="PNG", optimize=True)
    print(f"built {destination.name}: {image.width}x{image.height}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("utilities", type=Path, help="Path to the Utilities repository")
    args = parser.parse_args()

    notebooks = args.utilities / "jupyter_notebooks"
    destination = Path(__file__).resolve().parents[1] / "images" / "code"

    previews = {
        "JAX/obc_JAX.ipynb": "obc-jax.png",
        "JAX/default_LT_JAX.ipynb": "default-jax.png",
        "ASG/obc_ASG_julia.ipynb": "obc-asg-julia.png",
        "ASG/obc_ASG_python.ipynb": "obc-asg-python.png",
        "ASG/default_LT_ASG_julia.ipynb": "default-asg-julia.png",
        "ANN/obc_ANN_torch.ipynb": "obc-ann-pytorch.png",
    }
    for relative_path, filename in previews.items():
        save(saved_png(notebooks / relative_path), destination / filename)
    save(
        flux_preview(notebooks / "ANN/obc_ANN_flux.ipynb"),
        destination / "obc-ann-flux.png",
    )


if __name__ == "__main__":
    main()
