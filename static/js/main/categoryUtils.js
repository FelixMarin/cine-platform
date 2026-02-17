function formatCategoryName(cat) {
    // Si contiene /, tomar la parte después de la última /
    let cleanName = cat.includes('/') ? cat.split('/').pop() : cat;

    // Reemplazar guiones bajos por espacios
    cleanName = cleanName.replace(/_/g, " ");

    // Capitalizar cada palabra respetando acentos
    return cleanName.split(' ').map(word => {
        if (word.length === 0) return word;
        // Preservar la primera letra con su acento y poner el resto en minúsculas
        return word.charAt(0).toLocaleUpperCase() + word.slice(1).toLocaleLowerCase();
    }).join(' ');
}

window.formatCategoryName = formatCategoryName;