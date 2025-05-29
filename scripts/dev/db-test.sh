#!/bin/bash
moledb init database
molemarshal sync subjects workflow
molemarshal sync subject-sets project
molemarshal sync classifications
