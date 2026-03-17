from app.services.scoring import quali_points, status_points, bucket_from_total


def test_quali_points():
    assert quali_points(1) == 5
    assert quali_points(4) == 3
    assert quali_points(7) == 2
    assert quali_points(12) == 1
    assert quali_points(20) == 0


def test_status_points():
    assert status_points("classified") == 0
    assert status_points("dnf") == -10
    assert status_points("dns") == -10
    assert status_points("dsq") == -15


def test_bucket():
    assert bucket_from_total(40) == "LE40"
    assert bucket_from_total(41) == "MID80"
    assert bucket_from_total(80) == "MID80"
    assert bucket_from_total(81) == "GT80"
