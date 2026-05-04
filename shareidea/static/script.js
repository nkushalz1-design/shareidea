document.addEventListener("DOMContentLoaded", () => {

  // 🌙 DARK MODE
  const toggle = document.querySelector(".dark-btn");

  if (localStorage.getItem("mode") === "dark") {
    document.body.classList.add("dark");
  }

  toggle?.addEventListener("click", () => {
    document.body.classList.toggle("dark");

    localStorage.setItem(
      "mode",
      document.body.classList.contains("dark") ? "dark" : "light"
    );
  });

  // 📤 MODAL
  window.openUpload = () => {
  document.getElementById("uploadModal").classList.add("show");
};

window.closeUpload = () => {
  document.getElementById("uploadModal").classList.remove("show");
};

  // 🎯 CATEGORY
  window.selectCategory = (cat, el) => {
    document.getElementById("categoryInput").value = cat;

    document.querySelectorAll(".category-buttons button")
      .forEach(btn => btn.classList.remove("active"));

    el.classList.add("active");
  };

  // 🚨 VALIDATION
  window.validateUpload = () => {
    const cat = document.getElementById("categoryInput").value;

    if (!cat) {
      alert("Select category!");
      return false;
    }
    return true;
  };

  // ❤️ LIKE ANIMATION
  document.querySelectorAll(".like-btn").forEach(btn => {
    btn.addEventListener("click", () => {

      btn.classList.toggle("liked");

btn.animate([
  { transform: "scale(1)" },
  { transform: "scale(1.5)" },
  { transform: "scale(1)" }
], { duration: 300 });
      setTimeout(() => btn.style.transform = "scale(1)", 200);
    });
  });

  // 🔍 TAG FILTER
  const tags = document.querySelectorAll(".tag");
  const cards = document.querySelectorAll(".card");

  tags.forEach(tag => {
    tag.addEventListener("click", () => {
      document.querySelector(".tag.active")?.classList.remove("active");
      tag.classList.add("active");

     let selected = tag.getAttribute("data-category");

      cards.forEach(card => {
        let cat = card.dataset.category;

        if (selected === "All" || selected === cat) {
          card.style.display = "block";
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  // 📷 IMAGE PREVIEW
  const fileInput = document.getElementById("fileInput");
  const preview = document.getElementById("preview");

  fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0];
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  });

  // 🔥 DRAG DROP
  const dropArea = document.getElementById("dropArea");

  dropArea?.addEventListener("dragover", e => {
    e.preventDefault();
    dropArea.style.border = "2px dashed #6366f1";
  });

  dropArea?.addEventListener("dragleave", () => {
    dropArea.style.border = "none";
  });

  dropArea?.addEventListener("drop", e => {
    e.preventDefault();
    fileInput.files = e.dataTransfer.files;

    const file = fileInput.files[0];
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  });

});

// ⭐ SAVE BUTTON
function saveIdea(btn) {
  btn.innerText = "Saved ⭐";
btn.classList.add("saved");

btn.animate([
  { transform: "scale(1)" },
  { transform: "scale(1.4)" },
  { transform: "scale(1)" }
], { duration: 300 });
  setTimeout(() => btn.style.transform = "scale(1)", 200);
}

// ==============================
// 👤 PROFILE SYSTEM (FINAL FIX)
// ==============================

// OPEN PROFILE
function openProfile() {
  const panel = document.getElementById("profilePanel");
  panel.classList.add("show");
  loadProfile();
}

// CLOSE PROFILE
function closeProfile() {
  const panel = document.getElementById("profilePanel");
  panel.classList.remove("show");
}

// 🔥 LOAD PROFILE DATA
function loadProfile() {
  fetch("/get-profile")
    .then(res => res.json())
    .then(data => {
      if (!data.username) return;

      document.getElementById("profileName").innerText = data.username;
      document.getElementById("profileEmail").innerText = data.email;
      document.getElementById("editName").value = data.username;
      document.getElementById("editEmail").value = data.email;

      // ✅ AVATAR
      const img = document.getElementById("profileImg");

// 🔥 if user has uploaded image → use it
if (data.profile_pic && data.profile_pic !== "default.png") {
  img.src = "/static/uploads/" + data.profile_pic;
} else {
  // 🔥 fallback avatar
  img.src = "https://api.dicebear.com/7.x/initials/svg?seed=" + data.username;
}

      // ✅ PREMIUM FIX (IMPORTANT)
      const badge = document.getElementById("premiumBadge");
      badge.style.display = data.is_premium ? "block" : "none";
    });
}

// 🔥 CLICK OUTSIDE TO CLOSE (SAFE VERSION)
document.addEventListener("click", function (e) {
  const panel = document.getElementById("profilePanel");
  const card = document.querySelector(".profile-card");

  if (!panel || !card) return;

  if (
    panel.classList.contains("show") &&
    !card.contains(e.target) &&
    !e.target.closest(".fa-user-circle")
  ) {
    closeProfile();
  }
});

// 🔥 ESC KEY CLOSE
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeProfile();
  }
});