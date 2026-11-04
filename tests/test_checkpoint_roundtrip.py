import torch


def test_checkpoint_roundtrip(tmp_path):
    checkpoint = tmp_path / "last_checkpoint.pth"
    expected = {"epoch": 2, "best_f1": 0.71, "model": {"weight": torch.tensor([1.0])}, "optimizer": {"lr": 0.0003}, "scheduler": {"best": 0.71}}
    torch.save(expected, checkpoint)
    restored = torch.load(checkpoint, map_location="cpu")
    assert restored["epoch"] == 2
    assert restored["best_f1"] == 0.71
    assert torch.equal(restored["model"]["weight"], expected["model"]["weight"])
