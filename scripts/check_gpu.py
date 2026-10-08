import torch


def main() -> None:

    print(
        "PyTorch:",
        torch.__version__,
    )

    print(
        "CUDA available:",
        torch.cuda.is_available(),
    )

    if not torch.cuda.is_available():
        return

    print(
        "CUDA version:",
        torch.version.cuda,
    )

    print(
        "GPU count:",
        torch.cuda.device_count(),
    )

    print(
        "GPU:",
        torch.cuda.get_device_name(0),
    )

    properties = (
        torch.cuda.get_device_properties(
            0
        )
    )

    memory_gb = (
        properties.total_memory
        / 1024**3
    )

    print(
        f"VRAM: {memory_gb:.2f} GB"
    )


if __name__ == "__main__":
    main()