import os
import torch
import numpy as np
import cv2
from tqdm import tqdm
from Wav2Lip.models.wav2lip import Wav2Lip
from Wav2Lip.audio import load_wav, melspectrogram
import argparse

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def load_model(checkpoint_path):
    print("Loading Wav2Lip model...")
    model = Wav2Lip()
    checkpoint = torch.load(checkpoint_path, map_location=device)
    state_dict = checkpoint["state_dict"]
    model.load_state_dict({k.replace("module.", ""): v for k, v in state_dict.items()})
    model = model.to(device).eval()
    print("Model loaded.")
    return model

def preprocess_image(image_path, resize_factor=1, crop=None):
    """Load a single image and preprocess it."""
    print(f"Loading image from {image_path}...")
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Image file {image_path} not found.")
    if resize_factor > 1:
        frame = cv2.resize(frame, (frame.shape[1] // resize_factor, frame.shape[0] // resize_factor))
    if crop:
        x1, y1, x2, y2 = crop
        frame = frame[y1:y2, x1:x2]
    print("Image loaded and preprocessed.")
    return [frame]  # Return as a list to mimic video frames

def preprocess_audio(audio_path, fps, mel_step_size=16):
    """Load and process the audio file into mel chunks."""
    print(f"Processing audio from {audio_path}...")
    wav = load_wav(audio_path, 16000)
    mel = melspectrogram(wav)
    mel_chunks = []
    mel_idx_multiplier = 80.0 / fps

    i = 0
    while True:
        start_idx = int(i * mel_idx_multiplier)
        if start_idx + mel_step_size > mel.shape[1]:
            # Handle the last chunk with padding
            chunk = mel[:, start_idx:]
            chunk = np.pad(chunk, ((0, 0), (0, mel_step_size - chunk.shape[1])), mode="constant")
            mel_chunks.append(chunk)
            break
        mel_chunks.append(mel[:, start_idx:start_idx + mel_step_size])
        i += 1

    print(f"Generated {len(mel_chunks)} mel chunks.")
    return np.array(mel_chunks)

def datagen(frames, mels, img_size):
    """Generator to batch frames and mel spectrograms."""
    img_batch, mel_batch = [], []
    for i, mel in enumerate(mels):
        frame = cv2.resize(frames[0], (img_size, img_size))  # Use the single frame repeatedly
        img_batch.append(frame)
        mel_batch.append(mel)

        if len(img_batch) >= 1:  # Process one frame per mel chunk
            yield prepare_batch(img_batch, mel_batch, img_size)
            img_batch, mel_batch = [], []

    if len(img_batch) > 0:
        yield prepare_batch(img_batch, mel_batch, img_size)

def prepare_batch(img_batch, mel_batch, img_size):
    """Prepare image and mel batches."""
    img_batch = np.asarray(img_batch)
    mel_batch = np.asarray(mel_batch)

    # Mask lower half of the face for Wav2Lip input
    img_masked = img_batch.copy()
    img_masked[:, img_size // 2:] = 0
    img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.0

    mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

    return torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device), \
           torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)

def generate_lip_sync(image_path, audio_path, checkpoint_path, output_path, resize_factor=1, crop=None):
    print("Starting lip-sync process...")
    fps = 25  # Default FPS

    frames = preprocess_image(image_path, resize_factor=resize_factor, crop=crop)
    mel_chunks = preprocess_audio(audio_path, fps)

    # Load model
    model = load_model(checkpoint_path)

    # Initialize video writer
    frame_h, frame_w = frames[0].shape[:2]
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_w, frame_h))

    img_size = 96  # Wav2Lip's expected input image size
    gen = datagen(frames, mel_chunks, img_size)

    for img_batch, mel_batch in tqdm(gen, total=len(mel_chunks), desc="Synthesizing frames"):
        with torch.no_grad():
            pred = model(mel_batch, img_batch)
        pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.0

        for p in pred:
            out.write(cv2.resize(p.astype(np.uint8), (frame_w, frame_h)))

    out.release()
    print(f"Lip-synced video saved to {output_path}")






# import os
# import torch
# import numpy as np
# import cv2
# from glob import glob
# from tqdm import tqdm
# from torchvision import transforms
# from Wav2Lip.models import Wav2Lip
# from Wav2Lip.audio import load_wav, melspectrogram

# device = 'cuda' if torch.cuda.is_available() else 'cpu'

# def load_model(checkpoint_path):
#     print("Loading model...")
#     model = Wav2Lip()
#     checkpoint = torch.load(checkpoint_path, map_location=device)
#     model.load_state_dict(checkpoint['state_dict'])
#     model = model.to(device).eval()
#     print("Model loaded.")
#     return model

# def generate_lip_sync(face_path, audio_path, checkpoint_path, output_path):
#     print("Processing video and audio for lip-sync...")

#     # Load the face frames
#     video_frames = []
#     cap = cv2.VideoCapture(face_path)
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         video_frames.append(frame)
#     cap.release()
#     print(f"Loaded {len(video_frames)} video frames.")

#     # Load and process audio
#     wav = load_wav(audio_path, 16000)
#     mel = melspectrogram(wav)
#     mel_chunks = []
#     mel_step_size = 16
#     mel_idx_multiplier = 80.0 / 25.0

#     i = 0
#     while 1:
#         start_idx = int(i * mel_idx_multiplier)
#         if start_idx + mel_step_size > mel.shape[1]:
#             # Handle the last chunk by padding to match mel_step_size
#             chunk = mel[:, start_idx:]
#             chunk = np.pad(chunk, ((0, 0), (0, mel_step_size - chunk.shape[1])), mode='constant')
#             mel_chunks.append(chunk)
#             break
#         mel_chunks.append(mel[:, start_idx: start_idx + mel_step_size])
#         i += 1

#     mel_chunks = np.array(mel_chunks)
#     print(f"Generated {len(mel_chunks)} mel chunks of shape: {mel_chunks[0].shape}")


#     # Prepare the model
#     model = load_model(checkpoint_path)
#     print("Loaded Wav2Lip model.")

#     # Prepare output video writer
#     frame_h, frame_w = video_frames[0].shape[:2]
#     out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), 25, (frame_w, frame_h))

#     # Generate frames
#     for i, mel_chunk in enumerate(tqdm(mel_chunks, desc="Synthesizing frames")):
#         mel_tensor = torch.FloatTensor(mel_chunk).unsqueeze(0).unsqueeze(0).to(device)
#         frame_tensor = torch.FloatTensor(video_frames[i]).unsqueeze(0).permute(0, 3, 1, 2).to(device) / 255.0
#         with torch.no_grad():
#             pred = model(mel_tensor, frame_tensor)
#         pred_frame = (pred[0].cpu().numpy().transpose(1, 2, 0) * 255).astype(np.uint8)
#         out.write(pred_frame)

#     out.release()
#     print(f"Lip-synced video saved to {output_path}")
