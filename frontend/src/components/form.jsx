
// src/components/SubmitForm.jsx
import { useState } from 'react';

export default function Form() {
	const [url, setUrl] = useState("");
	const [result, setResult] = useState(null);

	const handleSubmit = async (e) => {
		e.preventDefault();
		const response = await fetch('http://localhost:8000/analyze', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ text: url })
		});
		const data = await response.json();
		setResult(data);
	};

	return (
		<>
			<form onSubmit={handleSubmit}>
				<input
					type="url"
					value={url}
					onChange={(e) => setUrl(e.target.value)}
					placeholder="Enter URL"
				/>
				<button type="submit">Submit</button>
			</form>

			{result && (
				<div>
					<p>Link: {result.link}</p>
					<p>Confidence: {result.confidence_score}</p>
					<p>Explanation: {result.explanation}</p>
				</div>
			)}
		</>
	);
}
