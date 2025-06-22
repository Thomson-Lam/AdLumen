// src/components/SubmitForm.jsx
import { useState } from 'react';
import { Send } from 'lucide-react';

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
				body: JSON.stringify({ url })
			});

			if (!response.ok) {
				throw new Error(`Server error: ${response.status}`);
			}

			// display the data; TODO: Change the format of data displayed, map it and make it look nice! 
			const data = await response.json();
			setResult(data); 
		} catch (err) {
			setError(err.message); // render error message 
		} finally {
			setLoading(false);
		}
	}

	return(
		<>
			<form onSubmit={handleSubmit} className="flex flex-row gap-x-2 justify-center items-center mb-10 w-[90vw] h-[10vh]">
				<input
					type="url"
					value={url}
					onChange={(e) => setUrl(e.target.value)}
					placeholder="Enter URL"
					required 
					className="px-2 w-full h-full text-xl text-white rounded-lg border border-white transition duration-300 ease-in-out focus:text-black focus:bg-white focus:ring focus:ring-amber-500"
				/>
				<button type="submit" className="ml-5 transition transform hover:scale-110">
					<Send size={60} color="white" />
				</button>
			</form>

			{loading && <p>Loading...</p>}
			{error && <p className="text-red-500">Error: {error}</p>}
			
			{result && (
				<div className="results-container">
					<h3>Analysis Results</h3>
					{result.error ? (
						<p className="error">Error: {result.error}</p>
					) : (
						<div className="analysis-results">
							<div className="result-item">
								<strong>URL:</strong> {result.url}
							</div>
							<div className="result-item">
								<strong>Fraud Probability:</strong> {(result.fraud_probability * 100).toFixed(1)}%
							</div>
							<div className="result-item">
								<strong>Confidence Level:</strong> {(result.confidence_level * 100).toFixed(1)}%
							</div>
							<div className="result-item">
								<strong>Summary:</strong> {result.justification}
							</div>
						</div>
					)}
				</div>
			)}
		</>
	);
}
