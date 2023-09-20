const {createApp, ref, onUpdated, computed, watch, nextTick} = Vue

document.addEventListener('DOMContentLoaded', (event) => {
    const blocksInput = document.getElementById("id_blocks");
    const blocksInputValue = blocksInput.value;
    blocksInput.value = "";
    const qualifications = JSON.parse(document.getElementById("qualifications_json").value);

    createApp({
        setup() {
            const currentBlock = ref(null);
            const blocks = ref(blocksInputValue ? JSON.parse(blocksInputValue) : []);
            blocks.value.forEach(block => {
                block.deleted = false;
                block.positions.forEach(position => {
                    position.clientId = `${position.id}`;
                });
                block.qualification_requirements.forEach(requirement => {
                    requirement.clientId = `${requirement.id}`;
                });
            });

            async function addBlock(block_type) {
                const newBlock = {
                    block_type: block_type,
                    name: "",
                    allowMore: false,
                    positions: [],
                    qualification_requirements: [],
                    sub_compositions: [],
                    id: null,
                    uuid: self.crypto.randomUUID(),
                }
                blocks.value.push(newBlock);
                currentBlock.value = newBlock;
                await nextTick()
                document.getElementById("block-name").focus();
            }

            function selectBlock(block) {
                currentBlock.value = block;
            }

            function removeBlock(block) {
                block.deleted = true;
                if (!block.id) {
                    // remove block from list if it was not saved yet
                    blocks.value = blocks.value.filter(b => b.uuid !== block.uuid);
                }
                if (currentBlock.value === block) {
                    currentBlock.value = null;
                }
            }

            function addPosition(e) {
                currentBlock.value.positions.push({
                        optional: false,
                        label: "",
                        qualifications: [],
                        id: null,
                        clientId: `new-${Math.random().toString(36).substring(7)}`,
                    }
                );
            }

            function removePosition(position) {
                currentBlock.value.positions = currentBlock.value.positions.filter(p => p.clientId !== position.clientId);
            }

            function addQualificationRequirement(e) {
                currentBlock.value.qualification_requirements.push({
                        id: null,
                        clientId: `new-${Math.random().toString(36).substring(7)}`,
                        qualifications: [],
                        at_least: 1,
                        everyone: false,
                    }
                );
            }

            function removeQualificationRequirement(requirement) {
                currentBlock.value.qualification_requirements = currentBlock.value.qualification_requirements.filter(r => r.clientId !== requirement.clientId);
            }

            function addQualificationToObject(event, object) {
                if (!event.target.value) {
                    return;
                }
                // add new qualification to list
                const newQualification = {
                    id: event.target.value,
                    title: event.target.options[event.target.selectedIndex].text,
                    abbreviation: qualifications[event.target.value].abbreviation,
                };
                event.target.value = "";
                // return if the pk already exists in the list
                if (!object.qualifications.some(q => q.id === newQualification.id)) {
                    object.qualifications.push(newQualification);
                }
            }

            function removeQualificationFromObject(position, object) {
                position.qualifications = position.qualifications.filter(q => q.id !== object.id);
            }


            onUpdated(() => {
                handleForms($('#editor'));
            });

            function getBlockByUUID(uuid) {
                return blocks.value.find(b => b.uuid === uuid);
            }

            function getSubBlocks(block) {
                const subBlocks = [];
                block.sub_compositions.forEach(composition => {
                    const sub_block = getBlockByUUID(composition.sub_block);
                    if(!sub_block) {
                        return;
                    }
                    subBlocks.push(sub_block);
                });
                return subBlocks;
            }

            function getParticipantCount(block) {
                let min = 0;
                let max = 0;
                let allowMore = false;

                getSubBlocks(block).forEach(sub_block => {
                    const {min: sub_min, max: sub_max, allowMore: sub_allowMore} = getParticipantCount(sub_block);
                    min += sub_min;
                    max += sub_max;
                    allowMore = allowMore || sub_allowMore;
                });

                block.positions.forEach(position => {
                    if (!position.optional) {
                        min += 1;
                    }
                    max += 1;
                });
                allowMore = allowMore || block.allowMore;
                return {min, max, allowMore};
            }

            function participantCountInfo(block) {
                const {min, max, allowMore} = getParticipantCount(block);
                if (allowMore) {
                    return gettext("{min}+").replace("{min}", min);
                }
                if (min === max) {
                    return min;
                }
                return gettext("{min} to {max}").replace("{min}", min).replace("{max}", max);
            }

            const undeletedBlocks = computed(() => blocks.value.filter(b => !b.deleted));


            return {
                blocks,
                currentBlock,
                undeletedBlocks,

                addBlock,
                selectBlock,
                removeBlock,

                addPosition,
                removePosition,
                addQualificationToObject,
                removeQualificationFromObject,
                addQualificationRequirement,
                removeQualificationRequirement,

                participantCountInfo,
                getSubBlocks,
                getBlockByUUID,
            }
        },
        delimiters: ['[[', ']]']
    }).mount('#editor');
});