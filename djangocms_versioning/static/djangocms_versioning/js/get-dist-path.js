const getDistPath = function(scriptFileName) {
    const fileNameReplaceRegExp = new RegExp(scriptFileName + '.*$', 'gi');

    if (document.currentScript) {
        return document.currentScript.src.replace(fileNameReplaceRegExp, '');
    }
    let scripts;
    let scriptUrl;
    const getSrc = function(listOfScripts, attr) {
        let fileName;
        let scriptPath;

        for (let i = 0; i < listOfScripts.length; i++) {
            scriptPath = null;
            if (listOfScripts[i].getAttribute.length !== undefined) {
                scriptPath = listOfScripts[i].getAttribute(attr, 2);
            }
            if (!scriptPath) {
                continue; // eslint-disable-line
            }
            fileName = scriptPath;
            fileName = fileName.split('?')[0].split('/').pop(); // get script filename
            if (fileName.match(fileNameReplaceRegExp)) {
                return scriptPath;
            }
        }
    };

    scripts = document.getElementsByTagName('script');
    scriptUrl = getSrc(scripts, 'src');
    if (scriptUrl) {
        return scriptUrl.replace(fileNameReplaceRegExp, '');
    }
    return '';
};

export default getDistPath;
