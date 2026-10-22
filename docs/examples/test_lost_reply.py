"""Tests an explicitly synthetic contract, never a real service guarantee."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("lost_reply.py")


class LostReplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = None
        if PATH.exists():
            spec = importlib.util.spec_from_file_location("lost_reply", PATH)
            cls.demo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.demo)

    def setUp(self):
        self.assertIsNotNone(self.demo, "Teaching module is not implemented yet")

    def test_lost_reply_after_commit_leaves_effect(self):
        service = self.demo.ToyService(deduplicates=False)
        with self.assertRaises(self.demo.LostReply):
            service.submit("op-1", "add A", now=0, lose="after")
        self.assertEqual(service.effects, [("op-1", "add A")])

    def test_lost_reply_before_commit_leaves_no_effect(self):
        service = self.demo.ToyService(deduplicates=False)
        with self.assertRaises(self.demo.LostReply):
            service.submit("op-1", "add A", now=0, lose="before")
        self.assertEqual(service.effects, [])

    def test_client_observation_is_identical_before_and_after(self):
        observations = []
        for fault in ("before", "after"):
            service = self.demo.ToyService(deduplicates=False)
            try:
                service.submit("op-1", "add A", now=0, lose=fault)
            except self.demo.LostReply as error:
                observations.append(str(error))
        self.assertEqual(observations, ["reply unavailable", "reply unavailable"])

    def test_operation_id_alone_does_not_deduplicate(self):
        service = self.demo.ToyService(deduplicates=False)
        service.submit("op-1", "add A", now=0)
        service.submit("op-1", "add A", now=1)
        self.assertEqual(len(service.effects), 2)

    def test_durable_key_reuses_original_result(self):
        service = self.demo.ToyService()
        first = service.submit("op-1", "add A", now=0)
        second = service.submit("op-1", "add A", now=100)
        self.assertEqual((first, second, len(service.effects)), (1, 1, 1))

    def test_expiry_boundary_removes_guarantee_not_effect(self):
        service = self.demo.ToyService(lifetime=2)
        service.submit("op-1", "add A", now=0)
        self.assertEqual(service.submit("op-1", "add A", now=1), 1)
        self.assertEqual(service.submit("op-1", "add A", now=2), 2)
        self.assertEqual(len(service.effects), 2)

    def test_cache_hit_does_not_refresh_lifetime(self):
        service = self.demo.ToyService(lifetime=2)
        service.submit("op-1", "add A", now=0)
        service.submit("op-1", "add A", now=1)
        service.submit("op-1", "add A", now=2)
        self.assertEqual(len(service.effects), 2)

    def test_key_is_bound_to_payload_while_retained(self):
        service = self.demo.ToyService()
        service.submit("op-1", "add A", now=0)
        with self.assertRaises(ValueError):
            service.submit("op-1", "add B", now=1)
        self.assertEqual(len(service.effects), 1)

    def test_distinct_ids_are_distinct_operations(self):
        service = self.demo.ToyService()
        service.submit("op-1", "add A", now=0)
        service.submit("op-2", "add A", now=0)
        self.assertEqual(len(service.effects), 2)

    def test_invalid_time_and_fault_are_rejected_before_effects(self):
        service = self.demo.ToyService()
        for kwargs in ({"now": -1}, {"now": 0, "lose": "sometimes"}):
            with self.assertRaises(ValueError):
                service.submit("op-1", "add A", **kwargs)
        self.assertEqual(service.effects, [])


if __name__ == "__main__":
    unittest.main()
