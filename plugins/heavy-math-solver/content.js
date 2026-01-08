const btn = document.createElement("button");
btn.innerText = "Heavy Calc";
btn.style.cssText = "position:fixed; top:10px; right:10px; z-index:9999;";
document.body.appendChild(btn);

btn.onclick = async () => {
    console.log("Requesting Calculation (Triggers Lazy Load)...");
    const res = await fetch("http://localhost:5000/v1/inference/heavy-math-solver/solve", {
        method: "POST",
        body: JSON.stringify({ payload: { num: 100 } })
    });
    console.log(await res.json());
};