
// src/components/SubmitForm.jsx
import { useState } from 'react';

export default function Form() {
	const [url, setUrl] = useState("");
	const [result, setResult] = useState(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const handleSubmit = async (e) => {
		e.preventDefault();
		
		setLoading(true); // wait for it to load, do a manual suspense 
		setError(null);

		try {
			const response = await fetch('http://localhost:8000/analyze', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ text: url })
			});

			if (!response.ok) {
				throw new Error(`Server error:  ${response.status}`);
			}

			// display the data; TODO: Change the format of data displayed, map it and make it look nice! 
			const data = await response.json();
			setResult(data); 
		} catch (err) {
			setError(err.message); // render error message 
		} finally {
			setLoading(false);
		}

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
					required 
				/>
				<button type="submit">Submit</button>
			</form>

		 	{loading && <p>Loading...</p>}
      			{error && <p className="text-red-500">Error: {error}</p>}
			
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
