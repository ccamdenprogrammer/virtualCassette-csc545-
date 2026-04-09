"""
Tests for the parameter store component.
"""

import threading
import pytest

from realtime_audio_fx.models.parameters import EffectParameters, ParameterStore
from realtime_audio_fx import config


class TestEffectParameters:
    """Tests for EffectParameters dataclass."""

    def test_default_values(self):
        """Test default parameter values."""
        params = EffectParameters()

        assert params.speed == config.DEFAULT_SPEED
        assert params.pitch_semitones == config.DEFAULT_PITCH
        assert params.echo_mix == config.DEFAULT_ECHO_MIX
        assert params.reverb_mix == config.DEFAULT_REVERB_MIX
        assert params.output_gain_db == config.DEFAULT_OUTPUT_GAIN_DB

    def test_custom_values(self):
        """Test creating parameters with custom values."""
        params = EffectParameters(
            speed=1.5,
            pitch_semitones=5.0,
            echo_mix=0.3,
        )

        assert params.speed == 1.5
        assert params.pitch_semitones == 5.0
        assert params.echo_mix == 0.3


class TestParameterStore:
    """Tests for ParameterStore class."""

    def test_get_snapshot(self):
        """Test getting parameter snapshot."""
        store = ParameterStore()
        snapshot = store.get_snapshot()

        assert isinstance(snapshot, EffectParameters)
        assert snapshot.speed == config.DEFAULT_SPEED

    def test_update_single(self):
        """Test updating a single parameter."""
        store = ParameterStore()
        store.update(speed=1.5)

        snapshot = store.get_snapshot()
        assert snapshot.speed == 1.5

    def test_update_multiple(self):
        """Test updating multiple parameters."""
        store = ParameterStore()
        store.update(speed=1.5, pitch_semitones=5.0, echo_mix=0.3)

        snapshot = store.get_snapshot()
        assert snapshot.speed == 1.5
        assert snapshot.pitch_semitones == 5.0
        assert snapshot.echo_mix == 0.3

    def test_update_invalid_parameter(self):
        """Test that updating invalid parameter raises error."""
        store = ParameterStore()

        with pytest.raises(ValueError):
            store.update(invalid_param=1.0)

    def test_reset(self):
        """Test resetting parameters to defaults."""
        store = ParameterStore()
        store.update(speed=2.0, pitch_semitones=12.0)

        store.reset()

        snapshot = store.get_snapshot()
        assert snapshot.speed == config.DEFAULT_SPEED
        assert snapshot.pitch_semitones == config.DEFAULT_PITCH

    def test_get_value(self):
        """Test getting single parameter value."""
        store = ParameterStore()
        store.update(speed=1.5)

        value = store.get_value("speed")
        assert value == 1.5

    def test_set_value(self):
        """Test setting single parameter value."""
        store = ParameterStore()
        store.set_value("speed", 1.5)

        snapshot = store.get_snapshot()
        assert snapshot.speed == 1.5

    def test_thread_safety(self):
        """Test thread-safe access to parameters."""
        store = ParameterStore()
        errors = []

        def reader():
            for _ in range(1000):
                try:
                    snapshot = store.get_snapshot()
                    # Just verify we got valid data
                    assert isinstance(snapshot.speed, float)
                except Exception as e:
                    errors.append(e)

        def writer():
            for i in range(1000):
                try:
                    store.update(speed=1.0 + (i % 100) / 100)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_snapshot_is_copy(self):
        """Test that snapshot is a copy, not reference."""
        store = ParameterStore()
        snapshot1 = store.get_snapshot()

        store.update(speed=2.0)
        snapshot2 = store.get_snapshot()

        # Original snapshot should be unchanged
        assert snapshot1.speed == config.DEFAULT_SPEED
        assert snapshot2.speed == 2.0
