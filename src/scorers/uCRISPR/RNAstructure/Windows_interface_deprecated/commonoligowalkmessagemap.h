	ON_MESSAGE(ID_OLIGODONE, DisplayOligoWalk)
	//{{AFX_MSG_MAP(COligoWalk)
	ON_BN_CLICKED(IDC_CTBUTTON, OnCtbutton)
	ON_BN_CLICKED(IDC_REPORTBUTTON, OnReportbutton)
	ON_BN_CLICKED(IDSTART,OnStart)
	ON_EN_CHANGE(IDC_LENGTH, OnChangeLength)
	ON_NOTIFY(UDN_DELTAPOS, IDC_LENGTHSPIN, OnLengthSpin)
	ON_NOTIFY(UDN_DELTAPOS, IDC_STARTSPIN, OnStartSpin)
	ON_NOTIFY(UDN_DELTAPOS, IDC_STOPSPIN, OnStopSpin)
	ON_EN_CHANGE(IDC_START, OnChangeStart)
	ON_EN_CHANGE(IDC_STOP, OnChangeStop)
	//}}AFX_MSG_MAP
	ON_COMMAND(ID_TEMPERATURE, OnTemperature)