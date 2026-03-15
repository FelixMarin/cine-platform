/**
 * Profile Page - State
 */

let currentProfile = null;

function getCurrentProfile() {
    return currentProfile;
}

function setCurrentProfile(profile) {
    currentProfile = profile;
}

function clearCurrentProfile() {
    currentProfile = null;
}
