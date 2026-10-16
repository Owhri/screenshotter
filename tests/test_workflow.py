import threading
import unittest

from screenshotter import PROMPT
from screenshotter.workflow import Workflow


class WorkflowTests(unittest.TestCase):
    def test_image_and_exact_prompt_reach_chat_then_speech(self):
        calls = []

        def answer(image, prompt):
            calls.append(("chat", image, prompt))
            return "  The answer is 42.  "

        workflow = Workflow(answer, lambda text: calls.append(("speech", text)), lambda _: None)
        self.assertTrue(workflow.submit(b"actual image bytes"))
        workflow.close()
        self.assertEqual(calls, [("chat", b"actual image bytes", PROMPT), ("speech", "The answer is 42.")])
        self.assertEqual(PROMPT, "answer these attached questions accurately and concisely.")

    def test_repeated_hotkeys_cannot_queue_or_send_extra_images(self):
        entered, release = threading.Event(), threading.Event()
        images = []

        def answer(image, _):
            images.append(image)
            entered.set()
            self.assertTrue(release.wait(3))
            return "Answer"

        workflow = Workflow(answer, lambda _: None, lambda _: None)
        try:
            self.assertTrue(workflow.submit(b"first"))
            self.assertTrue(entered.wait(3))
            self.assertFalse(workflow.submit(b"duplicate"))
        finally:
            release.set()
            workflow.close()
        self.assertEqual(images, [b"first"])
        self.assertFalse(workflow.submit(b"after close"))

    def test_failure_does_not_speak_or_leave_worker_busy(self):
        statuses, spoken = [], []
        done = threading.Event()

        def status(text):
            statuses.append(text)
            if text.startswith("Request failed"):
                done.set()

        def fail(*_):
            raise TimeoutError("sensitive error detail")

        workflow = Workflow(fail, spoken.append, status)
        workflow.submit(b"image")
        workflow.close()
        self.assertTrue(done.is_set())
        self.assertFalse(workflow._busy)
        self.assertEqual(spoken, [])
        self.assertNotIn("sensitive error detail", " ".join(statuses))

    def test_empty_answer_is_not_spoken(self):
        spoken, statuses = [], []
        workflow = Workflow(lambda *_: " \n ", spoken.append, statuses.append)
        workflow.submit(b"image")
        workflow.close()
        self.assertEqual(spoken, [])
        self.assertTrue(any(s.startswith("Request failed: RuntimeError") for s in statuses))


if __name__ == "__main__":
    unittest.main()
