from youtube_transcript_api import YouTubeTranscriptApi

video_id = "y_woFP79F0Q"  # ID del video YouTube
transcript_list = YouTubeTranscriptApi().get_transcript(video_id)

# Ricostruisci il testo completo
full_text = " ".join([entry['text'] for entry in transcript_list])

print(full_text)