# chatbot/middle_modules/faster_whisper.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from faster_whisper import WhisperModel, BatchedInferencePipeline
from utils.queues import QueueSlot
import numpy as np
import utils.config
import time

class FasterWhisper(DummyMiddle):
    """Uses FasterWhisper to transcribe audio to text.
    
    """

    def action(self, i):
        try:
            audio_data = self.input_queue.get()

            if isinstance(audio_data, (bytes, bytearray)):
                audio_data = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
   
            if audio_data is not None and len(audio_data) > 0:
                start_time = time.time()
                utils.config.debug_print(f"[{self.name}] Transcribing audio on loop {i}")
                segments, info = self.model.transcribe(
                        audio_data, 
                        language=self.language if self.language else None, 
                        beam_size=self.beam_size, 
                        initial_prompt=self.initial_prompt if self.initial_prompt else None, 
                        suppress_tokens=self.suppress_tokens,
                        vad_filter=self.faster_whisper_vad_filter
                        )
                text = ""
                for segment in segments:
                    text += segment.text + " "
                utils.config.debug_print(f"[{self.name}] TEXT='{text}' CONF={info.language_probability:.3f} TIME={time.time() - start_time:.3f}")
                if len(self._output_queues['text']) > 0:
                    self._output_queues['text'].put(text)
                if len(self._output_queues['confidence']) > 0:
                    self._output_queues['confidence'].put(info.language_probability)
        except Exception as e:
            utils.config.debug_print(f"Error in FasterWhisper: {e}")

    def __init__(self, name="faster_whisper_stt", **args, ):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "string"
        self.model_path = args.get('model_path', "small")
        self.device = args.get('device', "cuda")
        self.compute_type = args.get('compute_type', "float32")
        self.device_index = args.get('device_index', 0)
        self.beam_size = args.get('beam_size', 5)
        self.initial_prompt = args.get('initial_prompt', None)
        self.suppress_tokens = args.get('suppress_tokens', None)
        self.faster_whisper_vad_filter = args.get('faster_whisper_vad_filter', True)
        self.normalize_audio = args.get('normalize_audio', False)
        self.language = args.get('language', None)

        self._output_queues['text'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['confidence'] = QueueSlot(self, 'output', datatype='float')
        self._output_queues['default'] = self._output_queues['text']

        utils.config.debug_print(f"[{self.name}] Using model {self.model_path} on {self.device} with {self.compute_type} compute type")
        self.model = WhisperModel(
                self.model_path, 
                device=self.device, 
                compute_type=self.compute_type, 
                device_index=self.device_index)
        self.model = BatchedInferencePipeline(model=self.model)
        utils.config.debug_print(f"[{self.name}] Model loaded")


middle_modules_class['faster_whisper'] = FasterWhisper

