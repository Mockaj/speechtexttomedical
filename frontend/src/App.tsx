import { useState, useEffect, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
	faPlay,
	faStop,
	faPause,
	faMicrophone,
	faCopy,
	faCheck,
} from "@fortawesome/free-solid-svg-icons";
import "./App.css";
import { AudioRecorder, useAudioRecorder } from "react-audio-voice-recorder";

function App() {
	const [transcriptionText, setTranscriptionText] = useState<string>("");
	const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
	const [copySuccess, setCopySuccess] = useState<boolean>(false); // New state to track copy success
	const [placeholder, setPlaceholder] = useState<string>(
		"Transcription output will appear here..."
	);
	const [showCopyButton, setShowCopyButton] = useState<boolean>(false);
	const recorderControls = useAudioRecorder();
	const apiUrl = import.meta.env.VITE_BACKEND_URL;
	const handleCopyText = useCallback(() => {
		navigator.clipboard.writeText(transcriptionText).then(
			() => {
				setCopySuccess(true);
				setTimeout(() => setCopySuccess(false), 2000);
			},
			(err) => {
				console.error("Could not copy text: ", err);
				setCopySuccess(false);
			}
		);
	}, [transcriptionText]);

	useEffect(() => {
		if (isTranscribing) {
			const dots = [".", "..", "...", "....", "....."];
			let currentDot = 0;
			const intervalId = setInterval(() => {
				setPlaceholder(`Transcription in progress${dots[currentDot]}`);
				currentDot = (currentDot + 1) % dots.length;
			}, 300); // Update every 300 milliseconds

			return () => clearInterval(intervalId); // Cleanup interval on component unmount or state change
		} else {
			setPlaceholder("Transcription output will appear here...");
		}
	}, [isTranscribing]);

	// Effect to add event listener for keyboard shortcuts
	useEffect(() => {
		const handleKeyDown = (event: KeyboardEvent) => {
			// Check for Cmd on macOS or Ctrl on Windows/Linux and the 'K' key
			if ((event.metaKey || event.ctrlKey) && event.key === "k") {
				event.preventDefault(); // Prevent the default action of the key press
				handleCopyText(); // Perform the copy action
			}
		};

		window.addEventListener("keydown", handleKeyDown);

		// Cleanup the event listener on component unmount
		return () => {
			window.removeEventListener("keydown", handleKeyDown);
		};
	}, [transcriptionText, handleCopyText]);

	const handleTranscribeAudio = async () => {
		setIsTranscribing(true); // Start indicating transcription process
		try {
			const transcriptionResponse = await fetch(`${apiUrl}/transcribe`, {
				method: "GET",
			});
			const transcriptionData = await transcriptionResponse.json();
			if (transcriptionResponse.ok) {
				setTranscriptionText(
					transcriptionData.transcription ||
						"Error transcribing audio. Please try again."
				);
			} else {
				throw new Error(transcriptionData.error || "Failed to transcribe file");
			}
		} catch (error) {
			console.error("Error during transcription:", error);
			setTranscriptionText("Error processing audio. Please try again.");
		}
		setIsTranscribing(false);
		setShowCopyButton(true); // Show copy button after transcription finishes
		// End indicating transcription process
	};

	const handleUploadAudio = async (blob: Blob) => {
		const formData = new FormData();
		formData.append("file", blob, "recording.webm");
		try {
			await fetch(`${apiUrl}/upload`, {
				method: "POST",
				body: formData,
			});
			handleTranscribeAudio();
		} catch (error) {
			console.error("Error during upload:", error);
			setIsTranscribing(false); // Ensure we stop indicating transcription if upload fails
		}
	};

	return (
		<div className="App">
			<header className="App-header">
				<h1>Speech to Text</h1>
			</header>
			<div className="audio-recorder">
				<AudioRecorder
					onRecordingComplete={handleUploadAudio}
					recorderControls={recorderControls}
					audioTrackConstraints={{
						noiseSuppression: true,
						echoCancellation: true,
					}}
					downloadOnSavePress={false}
					downloadFileExtension="webm"
					showVisualizer={true}
				/>
			</div>
			<div className="transcription-container">
				{showCopyButton && (
					<button
						className="copy-button"
						onClick={handleCopyText}
						title="Copy to Clipboard">
						<FontAwesomeIcon icon={copySuccess ? faCheck : faCopy} />
					</button>
				)}
				<textarea
					className="transcription-area"
					placeholder={placeholder}
					readOnly
					value={transcriptionText}></textarea>
			</div>
			<footer className="App-footer">
				{recorderControls.isRecording ? (
					<>
						<button
							onClick={() => recorderControls.stopRecording()}
							className="control-button">
							<FontAwesomeIcon icon={faStop} /> Stop Recording
						</button>
						<button
							onClick={recorderControls.togglePauseResume}
							className="control-button"
							disabled={!recorderControls.isRecording}>
							<FontAwesomeIcon
								icon={recorderControls.isPaused ? faMicrophone : faPause}
							/>
							{recorderControls.isPaused ? "Resume" : "Pause"}
						</button>
					</>
				) : (
					<button
						onClick={() => recorderControls.startRecording()}
						className="control-button">
						<FontAwesomeIcon icon={faPlay} /> Start Recording
					</button>
				)}
			</footer>
		</div>
	);
}

export default App;
