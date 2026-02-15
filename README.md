

<h1>🍳 Rasa Recipe Assistant (Rasa Pro)</h1>

<p>This project is a conversational cooking assistant built with <strong>Rasa Pro</strong>.</p>

<p>The assistant allows users to:</p>
<ul>
    <li>🔎 Search recipes by name</li>
    <li>🥕 Search recipes by ingredients</li>
    <li>🥗 Apply dietary restrictions (vegan, halal, lactose-intolerant, etc.)</li>
    <li>📋 View ingredients</li>
    <li>👨‍🍳 Get step-by-step cooking instructions</li>
</ul>

<h2>🚀 Installation Guide</h2>

<h3>1️⃣ Clone the Repository</h3>
<pre><code>git clone https://github.com/your-username/your-repository-name.git</code></pre>

<h3>2️⃣ Navigate to the RASA Folder</h3>
<pre><code>cd RASA</code></pre>

<h3>3️⃣ Create a Virtual Environment (Python 3.11 Required)</h3>
<p>This project requires <strong>Python 3.11</strong>.</p>

<p>If you don’t have <code>uv</code> installed:</p>
<pre><code>pip install uv</code></pre>

<p>Create the virtual environment:</p>
<pre><code>uv venv --python 3.11</code></pre>

<p>Activate it (Windows PowerShell):</p>
<pre><code>.venv\Scripts\activate</code></pre>

<h3>4️⃣ Ensure pip is Installed</h3>
<pre><code>python -m ensurepip --upgrade</code></pre>

<h3>5️⃣ Install Required Libraries</h3>
<pre><code>python -m pip install -r requirements.txt</code></pre>

<h3>6️⃣ Install Rasa Pro</h3>
<pre><code>uv pip install rasa-pro</code></pre>

<h3>7️⃣ Set Your Rasa Pro License Key</h3>
<p><strong>⚠️ Do NOT commit your license key to GitHub.</strong></p>

<pre><code>$env:RASA_LICENSE="YOUR_RASA_PRO_LICENSE_KEY_HERE"</code></pre>

<p>Verify installation:</p>
<pre><code>rasa --version</code></pre>

<h3>8️⃣ Extract the Recipe Dataset</h3>

<p>Navigate to:</p>
<pre><code>Rasa\rasa_assistant\projet\actions\</code></pre>

<p>Extract:</p>
<pre><code>RAW_recipes.rar</code></pre>

<p>To obtain:</p>
<pre><code>RAW_recipes.csv</code></pre>

<p><strong>⚠️ The assistant will not work without this CSV file.</strong></p>

<h2>🧠 Train the Model</h2>

<p>Go to:</p>
<pre><code>Rasa\rasa_assistant\projet\</code></pre>

<pre><code>rasa train</code></pre>

<p>After training:</p>
<pre><code>rasa inspect</code></pre>





<h2>⚙️ Features</h2>

<h3>🔍 Fuzzy Matching</h3>
<ul>
    <li>Uses <code>rapidfuzz</code> for ingredient and recipe matching</li>
    <li>Supports flexible user input (typos, partial names)</li>
</ul>

<h3>🥗 Dietary Restriction Filtering</h3>
<ul>
    <li>Vegetarian</li>
    <li>Vegan</li>
    <li>Halal</li>
    <li>Gluten-free</li>
    <li>Dairy-free</li>
    <li>Lactose-intolerant</li>
    <li>Kosher</li>
    <li>Nut-free</li>
    <li>Pescatarian</li>
</ul>

<h3>🚀 Performance Optimizations</h3>
<ul>
    <li>Precomputed ingredient texts</li>
    <li>Cached recipe name lists</li>
    <li>Limited candidate search before deep fuzzy scoring</li>
</ul>

<h2>📦 Requirements</h2>
<ul>
    <li>Python 3.11</li>
    <li>Rasa Pro</li>
    <li>uv</li>
    <li>pandas</li>
    <li>rapidfuzz</li>
</ul>

<h2>⚠️ Important Notes</h2>
<ul>
    <li>Always activate your virtual environment before running the project.</li>
    <li>Never share your Rasa Pro license key publicly.</li>
    <li>Ensure RAW_recipes.csv is extracted correctly.</li>
</ul>

<h2>🧪 Example Usage</h2>
<ul>
    <li>"I want to cook pizza"</li>
    <li>"Suggest recipes with avocado, bread, and cheese"</li>
    <li>"Give me the instructions"</li>
</ul>


</body>
</html>
