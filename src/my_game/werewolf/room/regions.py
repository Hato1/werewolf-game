from my_game.werewolf.room.loaders import RegionData

TEST_REGION = RegionData(
    name="Test Region",
    description="A region for testing purposes.",
    polygon=((10, 10), (100, 10), (100, 100), (10, 100)),
    id="test_region",
)
