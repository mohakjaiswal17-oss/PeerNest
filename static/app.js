document.addEventListener("DOMContentLoaded",()=>{
 document.querySelectorAll(".flash-close").forEach(b=>b.addEventListener("click",()=>b.closest(".flash")?.remove()));
 document.querySelectorAll("[data-toggle]").forEach(b=>b.addEventListener("click",()=>{const i=document.getElementById(b.dataset.toggle);if(!i)return;const show=i.type==="password";i.type=show?"text":"password";b.textContent=show?"Hide":"Show"}));
 document.querySelectorAll("form").forEach(f=>f.addEventListener("submit",()=>{const b=f.querySelector('button[type="submit"],button:not([type])');if(b&&f.checkValidity())b.classList.add("is-submitting")}));
 const s=document.getElementById("study_status");const y=document.querySelector('input[name="study_year"]');if(s&&y)s.addEventListener("change",()=>{y.placeholder=s.value==="Graduate"?"e.g. Graduated in 2025":"e.g. 2nd year"});
});
